import sys, pickle

import lapie
from parse_sdf import parse_sdf_file
import libpyprjoxide

import numpy as np
from scipy.sparse import csc_matrix
from scipy.sparse.linalg import lsqr

from os import path
import glob

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

def get_fanout_adder_variable(pipcls):
    v = (pipcls, "fanout_adder")
    if v not in var2idx:
        var2idx[v] = len(var_names)
        var_names.append(v)
    return var2idx[v]

# Equation system, we'll turn this into a proper sparse matrix later
eqn_rows = []

# Names of the different things we are solving
dly_types = ("min", "typ", "max")

max_cls_fanout = {}

def process_design(picklef, sdf):
    with open(picklef, "rb") as pf:
        parsed = pickle.load(pf)
        arc2pips = parsed["arc2pips"]
        wire_fanout = parsed["wire_fanout"]
    # Correlate with interconnect delays in the Tcl, and build equations
    parsed_sdf = parse_sdf_file(sdf).cells["top"]
    for from_pin, to_pin in sorted(parsed_sdf.interconnect.keys()):
        src = conv_sdf_port(from_pin)
        dst = conv_sdf_port(to_pin)
        if (src, dst) not in arc2pips:
            continue
        dly = parsed_sdf.interconnect[from_pin, to_pin]
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
            #fan_var = get_fanout_adder_variable(pipcls)
            #if fan_var is not None:
            #    fanout = wire_fanout.get(pip[0], 1)
            #    max_cls_fanout[pipcls] = max(max_cls_fanout.get(pipcls, 0), fanout)
            #    coeff[fan_var] = coeff.get(fan_var, 0) + fanout
        if skip_route:
            continue
        # AFAICS all Nexus delays are the same for rising and falling, so don't bother solving both
        rhs = (
            min(dly.rising.minv, dly.falling.minv),
            max(dly.rising.typv, dly.falling.typv),
            max(dly.rising.maxv, dly.falling.maxv),
        )
        eqn_rows.append((tuple(sorted(coeff.items())), rhs))

def main():
    # Import SDF and pickle files
    folder = sys.argv[1]
    grade = "12" if len(sys.argv) == 2 else sys.argv[2]

    for pickle in glob.glob(path.join(folder, "*.pickle")):
        sdf = pickle.replace("_route.pickle", "_{}.sdf".format(grade))
        if path.exists(sdf):
            print("Importing {}...".format(pickle))
            process_design(pickle, sdf)
        
    skip_vars = set()
    row_ind = []
    col_ind = []
    data_values = []
    rhs = []
    # Don't add a fanout variable where fanout is never seen
    #for pipcls, max_f in max_cls_fanout.items():
    #    if (pipcls, "fanout_adder") in var2idx:
    #        skip_vars.add(var2idx[(pipcls, "fanout_adder")])

    for i, row in enumerate(eqn_rows):
        coeff, dlys = row
        for j, val in coeff:
            if j in skip_vars:
                continue
            row_ind.append(i)
            col_ind.append(j)
            data_values.append(val)
        rhs.append(dlys[2])

    rows = len(eqn_rows)
    # Force skipped variables to zero
    for j in sorted(skip_vars):
        row_ind.append(rows)
        col_ind.append(j)
        data_values.append(1)
        rhs.append(0)
        rows += 1
    A = csc_matrix((data_values, (row_ind, col_ind)), (rows, len(var_names)))
    b = np.array(rhs)
    print("Running least squares solver...")
    x, istop, itn, r1norm = lsqr(A, b)[:4]
    for i, var in sorted(enumerate(var_names), key=lambda x: x[1]):
        print("{:40s} {:20s} {:6.0f}".format(var[0], var[1], x[i]))

if __name__ == '__main__':
    main()
