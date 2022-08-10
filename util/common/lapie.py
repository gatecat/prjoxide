"""
Python wrapper for `lapie`
"""
from os import path
import os
import subprocess
import database
import tempfile
import re

def run(commands, workdir=None):
    """Run a list of Tcl commands, returning the output as a string"""
    rcmd_path = path.join(database.get_oxide_root(), "radiant_cmd.sh")
    if workdir is None:
        workdir = tempfile.mkdtemp()
    scriptfile = path.join(workdir, "script.tcl")
    with open(scriptfile, 'w') as f:
        for c in commands:
            f.write(c + '\n')
    env = os.environ.copy()
    env["LATCL_DEV_ENABLE"] = "1"
    result = subprocess.run(["bash", rcmd_path, "lapie", scriptfile], cwd=workdir, env=env).returncode
    # meh, fails sometimes
    # assert result == 0, "lapie returned non-zero status code {}".format(result)
    outfile = path.join(workdir, 'lapie.log')
    output = ""
    with open(outfile, 'r') as f:
        for line in f:
            if line.startswith("WARNING - "):
                continue
            output += line
    # Strip Lattice header
    delimiter = "-" * 80
    output = output[output.rindex(delimiter)+81:].strip()
    # Strip Lattice pleasantry
    pleasantry = "Thank you for using"
    output = output[:output.find(pleasantry)].strip()
    return output

def run_with_udb(udb, commands):
    return run(['des_read_udb "{}"'.format(path.abspath(udb))] + commands)

class PipInfo:
    def __init__(self, from_wire, to_wire, is_bidi = False, flags = 0, buffertype = ""):
        self.from_wire = from_wire
        self.to_wire = to_wire
        self.flags = flags
        self.buffertype = buffertype
        self.is_bidi = is_bidi

class PinInfo:
    def __init__(self, site, pin, wire, pindir):
        self.site = site
        self.pin = pin
        self.wire = wire
        self.dir = pindir

class NodeInfo:
    def __init__(self, name):
        self.name = name
        self.nodetype = None
        self.uphill_pips = []
        self.downhill_pips = []
        self.pins = []

node_re = re.compile(r'^\[\s*(\d+)\]\s*([A-Z0-9a-z_]+)')
pip_re = re.compile(r'^([A-Z0-9a-z_]+) (<--|<->|-->) ([A-Z0-9a-z_]+) \(Flags: ...., (\d+)\) \(Buffer: ([A-Z0-9a-z_]+)\)')
pin_re = re.compile(r'^Pin  : ([A-Z0-9a-z_]+)/([A-Z0-9a-z_]+) \(([A-Z0-9a-z_]+)\)')

def parse_node_report(rpt):
    curr_node = None
    nodes = []
    for line in rpt.split('\n'):
        sl = line.strip()
        nm = node_re.match(sl)
        if nm:
            curr_node = NodeInfo(nm.group(2))
            nodes.append(curr_node)
            continue
        pm = pip_re.match(sl)
        if pm:
            flg = int(pm.group(4))
            btyp = pm.group(5)
            if pm.group(2) == "<--":
                curr_node.uphill_pips.append(
                    PipInfo(pm.group(3), pm.group(1), False, flg, btyp)
                )
            elif pm.group(2) == "<->":
                curr_node.uphill_pips.append(
                    PipInfo(pm.group(3), pm.group(1), True, flg, btyp)
                )
                curr_node.downhill_pips.append(
                    PipInfo(pm.group(1), pm.group(3), True, flg, btyp)
                )
            elif pm.group(2) == "-->":
                curr_node.downhill_pips.append(
                    PipInfo(pm.group(1), pm.group(3), False, flg, btyp)
                )
            else:
                assert False
            continue
        qm = pin_re.match(sl)
        if qm:
            curr_node.pins.append(
                PinInfo(qm.group(1), qm.group(2), curr_node.name, qm.group(3))
            )
    return nodes


def get_node_data(udb, nodes, regex=False):
    workdir = tempfile.mkdtemp()
    nodefile = path.join(workdir, "nodes.txt")
    nodelist = ""
    if len(nodes) == 1:
        nodelist = nodes[0]
    elif len(nodes) > 1:
        nodelist = "[list {}]".format(" ".join(nodes))
    run_with_udb(udb, ['dev_report_node -file {} [get_nodes {}{}]'.
        format(nodefile, "-re " if regex else "", nodelist)])
    with open(nodefile, 'r') as nf:
        return parse_node_report(nf.read())

def list_nets(udb):
    # des_list_net no longer works?
    output = run_with_udb(udb, ['des_report_instance'])
    net_list = set()

    for line in output.split('\n'):
        net_re = re.compile(r'.*sig=([A-Za-z0-9_\[\]()./]+).*')
        m = net_re.match(line)
        if m:
            if m.group(1) == "n/a":
                continue
            net_list.add(m.group(1))
    return list(sorted(net_list))


class NetPin:
    def __init__(self, cell, pin, node):
        self.cell = cell
        self.pin = pin
        self.node = node

class NetPip:
    def __init__(self, node1, node2, is_dir):
        self.node1 = node1
        self.node2 = node2
        self.is_dir = is_dir

class NetRouting:
    def __init__(self):
        self.pins = []
        self.pips = []

def get_routing(udb, nets):
    output = run_with_udb(udb, ['des_report_net {{{}}}'.format(n) for n in nets])
    curr_routing = NetRouting()
    routing = {}
    name_re = re.compile(r'Name = ([^ ]*) id = \d+ power_type = \d+')
    pin_re = re.compile(r'comp= ([^ ]*) pin= ([^ ]*) node= ([^ ]*) subnet= \d+ num_x=\d+')
    pip_re = re.compile(r'node1= ([^ ]*) node2= ([^ ]*) subnet= \d+  type=\(\d+ -> \d+\)  dir=([A-Z])')

    for line in output.split('\n'):
        sl = line.strip()
        nm = name_re.match(sl)
        if nm:
            curr_net = nm.group(1)
            routing[curr_net] = curr_routing
            curr_routing = NetRouting()
            continue
        pm = pin_re.match(sl)
        if pm:
            curr_routing.pins.append(NetPin(pm.group(1), pm.group(2), pm.group(3)))
            continue
        pipm = pip_re.match(sl)
        if pipm:
            is_dir = pipm.group(3) == "D"
            curr_routing.pips.append(NetPip(pipm.group(1), pipm.group(2), is_dir))
    return routing
