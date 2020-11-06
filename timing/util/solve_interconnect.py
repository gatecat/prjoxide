import sys, pickle, math, json, os, glob

import lapie
from parse_sdf import parse_sdf_file
import database
import libpyprjoxide

import numpy as np
from scipy.sparse import csc_matrix
from scipy.sparse.linalg import lsqr

from os import path

from timing_config import *

def unescape_sdf_name(name):
    e = ""
    if name[0] == '"':
        assert name[-1] == '"'
        name = name[1:-1]
    for c in name:
        if c == '\\':
            continue
        e += c
    return e

def conv_sdf_port(port):
    cell, _, pin = port.partition('/')
    return unescape_sdf_name(cell), unescape_sdf_name(pin)

def get_wirename(wire):
    rc, _, name = wire.partition('_')
    r, _, c = rc.partition('C')
    return (int(c), int(r[1:]), name)

def get_pip_class(pip):
    src_x, src_y, src_name = get_wirename(pip[0])
    dst_x, dst_y, dst_name = get_wirename(pip[1])
    return libpyprjoxide.classify_pip(src_x, src_y, src_name, dst_x, dst_y, dst_name)

# Keeping track of variable names
var_names = []
var2idx = {}
def get_base_variable(pipcls):
    v = (pipcls, "base")
    if v not in var2idx:
        var2idx[v] = len(var_names)
        var_names.append(v)
    return var2idx[v]


# Equation system, we'll turn this into a proper sparse matrix later
eqn_coeffs = []

# Names of the different things we are solving
dly_types = ("min", "typ", "max")

max_cls_fanout = {}

design_arc2row = {}

def process_design(picklef, templ_sdf):
    with open(picklef, "rb") as pf:
        parsed = pickle.load(pf)
        arc2pips = parsed["arc2pips"]
        wire_fanout = parsed["wire_fanout"]
    parsed_sdf = parse_sdf_file(templ_sdf, route_mode=True).cells["top"]
    # Based on the routing path in the pickle file; build a system of equations
    # counting the number of pips for each pip class in that row
    arc2row = {}
    for from_pin, to_pin in sorted(parsed_sdf.interconnect.keys()):
        src = conv_sdf_port(from_pin)
        dst = conv_sdf_port(to_pin)
        if (src, dst) not in arc2pips:
            # messed up IO buffer naming
            if src[0].endswith("_I") and ((src[0][:-2], src[1]), dst) in arc2pips:
                src = (src[0][:-2], src[1])
            elif dst[0].endswith("_I") and (src, (dst[0][:-2], dst[1])) in arc2pips:
                dst = (dst[0][:-2], dst[1])
            else:
                # print("skip missing {}, {}".format(src, dst))
                continue
        coeff = {}
        skip_route = False
        for pip in arc2pips[src, dst]:
            pipcls = get_pip_class(pip)
            if pipcls is None:
                skip_route = True
                break
            if pipcls in zero_delay_classes:
                continue
            base_var = get_base_variable(pipcls)
            if base_var is not None:
                coeff[base_var] = coeff.get(base_var, 0) + 1
        if skip_route:
            continue
        arc2row[(from_pin, to_pin)] = len(eqn_coeffs)
        eqn_coeffs.append(tuple(sorted(coeff.items())))
    design_arc2row[picklef.replace("_route.pickle", "")] = arc2row

def main():
    # Import SDF and pickle files
    folder = sys.argv[1]
    for pickle in glob.glob(path.join(folder, "*.pickle")):
        if path.exists(pickle.replace("_route.pickle", "_10.sdf")):
            print("Importing {}...".format(pickle))
            process_design(pickle, pickle.replace("_route.pickle", "_10.sdf"))
        
    row_ind = []
    col_ind = []
    data_values = []
    rhs = []
    for i, coeff in enumerate(eqn_coeffs):
        for j, val in coeff:
            row_ind.append(i)
            col_ind.append(j)
            data_values.append(val)
    rows = len(eqn_coeffs)
    A = csc_matrix((data_values, (row_ind, col_ind)), (rows, len(var_names)))
    bmin = np.zeros(rows)
    bmax = np.zeros(rows)

    speedgrades = ["4", "5", "6", "10", "11", "12", "M"]
    for speed in speedgrades:
        # For each speedgrade, set up the right hand side of the equation system by using
        # the delays in the interconnect section of the SDF file
        for design, arc2row in design_arc2row.items():
            sdf = "{}_{}.sdf".format(design, speed)
            parsed_sdf = parse_sdf_file(sdf, route_mode=True).cells["top"]
            for from_pin, to_pin in sorted(parsed_sdf.interconnect.keys()):
                if (from_pin, to_pin) not in arc2row:
                    continue
                dly = parsed_sdf.interconnect[from_pin, to_pin]
                bmin[arc2row[from_pin, to_pin]] = max(dly.rising.minv, dly.falling.minv)
                bmax[arc2row[from_pin, to_pin]] = max(dly.rising.maxv, dly.falling.maxv)
        print("Running least squares solver for speed {}...".format(speed))

        # Run the least squares solver on the system of equations
        xmin, istop, itn, r1norm = lsqr(A, bmin)[:4]
        xmax, istop, itn, r1norm = lsqr(A, bmax)[:4]

        delay_json = {"pip_classes": {}}

        for i, var in sorted(enumerate(var_names), key=lambda x: x[1]):
            print("  {:32s} {:20s} {:6.0f} {:6.0f}".format(var[0], var[1], xmin[i], xmax[i]))
            if var[0] not in delay_json["pip_classes"]:
                delay_json["pip_classes"][var[0]] = {}
            delay_json["pip_classes"][var[0]][var[1]] = [int(xmin[i] + 0.5), int(xmax[i] + 0.5)]
        for zd in sorted(zero_delay_classes):
            print("  {:32s} {:20s} {:6.0f} {:6.0f} (fixed)".format(zd, "base", 0, 0))
            delay_json["pip_classes"][zd] = dict(base=[0, 0])

        # Write JSON so it can be used as part of the database  import process
        timing_root = path.join(database.get_db_root(), "LIFCL", "timing")
        os.makedirs(timing_root, exist_ok=True)
        with open(path.join(timing_root, "interconnect_{}.json".format(speed)), "w") as jf:
            json.dump(delay_json, jf, indent=4, sort_keys=True)

        # Compute Ax and compare to b for a simple estimation of the model error
        for i, var in sorted(enumerate(var_names), key=lambda x: x[1]):
            if xmin[i] < 0:
                xmin[i] = 0
            if xmax[i] < 0:
                xmax[i] = 0
        min_err = 99999
        max_err = -99999
        rms_err = 0
        N = 0
        min_coeffs = {}
        for i, coeff in enumerate(eqn_coeffs):
            model = 0
            for j, val in coeff:
                model += val * xmax[j]
            err = model - bmax[i]
            if err < min_err:
                min_coeffs = coeff
                min_err = err
            min_err = min(err, min_err)
            max_err = max(err, max_err)
            rms_err += err ** 2
            N += 1

        print("  error: neg={:.1f}ps, max={:.1f}ps, rms={:.1f}ps".format(min_err, max_err, math.sqrt(rms_err/N)))
        print("            neg eqn {}".format(" + ".join("{}*{}".format(val, var_names[j][0]) for j, val in min_coeffs)))


if __name__ == '__main__':
    main()
