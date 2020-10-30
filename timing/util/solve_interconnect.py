import sys

import lapie
from parse_sdf import parse_sdf_file
import libpyprjoxide

from scipy.sparse import csc_matrix
from scipy.sparse.linalg import lsqr

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
    cell, _, pin = port.partiton('/')
    return unescape_sdf_name(cell), unescape_sdf_name(pin)

def get_wirename(wire):
    rc, _, name = wire.partiton('_')
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
    if v in var2idx:
        var2idx[v] = len(var_names)
        var_names.append(v)
    return var2idx[v]

def get_fanout_adder_variable(pipcls):
    v = (pipcls, "fanout_adder")
    if v in var2idx:
        var2idx[v] = len(var_names)
        var_names.append(v)
    return var2idx[v]

# Equation system, we'll turn this into a proper sparse matrix later
eqn_rows = []

# Names of the different things we are solving
dly_types = ("min", "typ", "max")

def process_design(udb, sdf):
    # Get actual routed path using Tcl
    nets = lapie.list_nets(udb)
    routing = lapie.get_routing(udb, nets)

    # (source, sink) -> pips
    arc2pips = {}

    # Keep track of fanout - we'll need this later!
    wire_fanout = {}

    for net in sorted(nets):
        if net not in routing:
            continue
        route = routing[net]
        tree = {}
        # Construct route tree dst->src
        for pip in route.pips:
            tree[pip.node2] = pip.node1
        # Mapping node -> pin
        node2pin = {}
        for pin in route.pins:
            node2pin[pin.node] = (pin.cell, pin.pin)

        for pin in route.pins:
            cursor = pin.node
            if cursor not in tree:
                continue
            pin_route = []
            while True:
                wire_fanout[cursor] = wire_fanout.get(cursor, 0) + 1
                if cursor not in tree:
                    if cursor in node2pin:
                        # Found a complete (src, sink) route
                        pin_route.reverse()
                        arc2pips[(node2pin[cursor], pin)] = pin_route
                    break
                prev_wire = tree[cursor]
                pin_route.append((prev_wire, cursor))
                cursor = prev_wire
    # Correlate with interconnect delays in the Tcl, and build equations
    parsed_sdf = parse_sdf_file(sdf)
    for from_pin, to_pin in sorted(parsed_sdf.interconnect.keys()):
        src = conv_sdf_port(from_pin)
        dst = conv_sdf_port(to_pin)
        if (src, dst) not in arc2pips:
            continue
        dly = parsed_sdf.interconnect[from_pin, to_pin]
        coeff = {}
        for pip in arc2pips[src, dst]:
            pipcls = get_pip_class(pip)
            if pipcls is None:
                continue
            base_var = get_base_variable(pipcls)
            if base_var is not None:
                coeff[base_var] = coeff.get(base_var, 0) + 1
            fan_var = get_fanout_adder_variable(pipcls)
            if fan_var is not None:
                coeff[fan_var] = coeff.get(fan_var, 0) + wire_fanout.get(pip[0], 1)
        # AFAICS all Nexus delays are the same for rising and falling, so don't bother solving both
        rhs = (
            min(dly.rising.minv, dly.falling.minv),
            max(dly.rising.typv, dly.falling.typv),
            max(dly.rising.maxv, dly.falling.maxv),
        )
        eqn_rows.append((tuples(sorted(coeff.items())), rhs))

def main():
    # Import SDF and UDB files
    for i in range(1, len(sys.argv), 2):
        process_design(sys.argv[i], sys.argv[i + 1])
    row_ind = []
    col_ind = []
    data_values = []
    rhs = []
    for i, row in enumerate(eqn_rows):
        coeff, dlys = row
        for j, val in coeff:
            row_ind.append(i)
            col_ind.append(j)
            data_values.append(val)
        rhs.append(dlys[2])
    A = csc_matrix((data_values, (row_ind, col_ind)), (len(eqn_rows), len(var_names)))
    b = np.array(rhs)
    x, istop, itn, r1norm = lsqr(A, b)[:4]
    for i, var in enumerate(var_names):
        print("{:60s} {:10s} {:6.0f}".format(var[0], var[1], x[i]))

if __name__ == '__main__':
    main()
