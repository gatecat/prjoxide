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
    assert result == 0, "lapie returned non-zero status code {}".format(result)
    outfile = path.join(workdir, 'lapie.log')
    with open(outfile, 'r') as f:
        output = f.read()
    # Strip Lattice header
    delimiter = "-" * 80
    output = output[output.rindex(delimiter)+81:].strip()
    # Strip Lattice pleasantry
    pleasantry = "Thank you for using"
    output = output[:output.find(pleasantry)].strip()
    return output

def run_with_udb(udb, commands):
    run(['des_read_udb "{}"'.format(path.abspath(udb))] + commands)

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
    run_with_udb(udb, ['dev_report_node -file {} [get_nodes {}{}]'.
        format(nodefile, "-re " if regex else "", " ".join(nodes))])
    with open(nodefile, 'r') as nf:
        return parse_node_report(nf.read())
