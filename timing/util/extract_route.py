import lapie
import pickle
import sys

def main():
    udb = sys.argv[1]
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

        for rpin in route.pins:
            pin = (rpin.cell, rpin.pin)
            cursor = rpin.node
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
    with open(sys.argv[2], "wb") as pf:
        pickle.dump(dict(arc2pips=arc2pips, wire_fanout=wire_fanout), pf)

if __name__ == '__main__':
    main()
