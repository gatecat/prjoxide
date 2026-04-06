"""
Python wrapper for `lapie`
"""
import asyncio
import hashlib
import itertools
import logging
import os
import re
import shutil
import sqlite3
import subprocess
import tempfile
import time
from collections import defaultdict
from functools import cache
from os import path

import cachier
import fuzzconfig

import cachecontrol
import database

radiant_version = database.get_radiant_version()

get_nodes = "dev_get_nodes"
if radiant_version == "2023":
    tcltool = "lark"
    tcltool_log = "radiantc.log"
    dev_enable_name = "RAT_DEV_ENABLE"
elif radiant_version == "2025" or radiant_version == "2024":
    # For whatever reason; these versions of the tool have a dependency on libqt 3 so finding a way to run it
    # might be challenging; even in a container environment. Included here for completeness; recommend running 2023
    # for tasks requiring this instead.
    tcltool = "labrus"
    tcltool_log = "radiantc.log"
    dev_enable_name = "RAT_DEV_ENABLE"    
else:
    tcltool = "lapie"
    tcltool_log = "lapie.log"
    dev_enable_name = "LATCL_DEV_ENABLE"
    get_nodes = "get_nodes"
    
def run(commands, workdir=None, stdout=None):
    from radiant import run_bash_script

    """Run a list of Tcl commands, returning the output as a string"""
    rcmd_path = path.join(database.get_oxide_root(), "radiant_cmd.sh")
    if workdir is None:
        workdir = tempfile.mkdtemp()
    scriptfile = path.join(workdir, "script.tcl")
    with open(scriptfile, 'w') as f:
        for c in commands:
            f.write(c + '\n')
    env = os.environ.copy()
    env[dev_enable_name] = "1"
    env["LSC_SHOW_INTERNAL_ERROR"] = "1"

    result_struct = run_bash_script(env, rcmd_path, tcltool, scriptfile, cwd=workdir, stdout=stdout)

    result = result_struct.returncode

    outfile = path.join(workdir, tcltool_log)
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

run_with_udb_cnt = 0
def run_with_udb(udb, commands, stdout = None):
    global run_with_udb_cnt
    run_with_udb_cnt = run_with_udb_cnt + 1
    if not udb.endswith(".udb"):
        device = udb
        udb = f"/tmp/prjoxide_node_data/{device}.udb"
        if not os.path.exists(udb):
            config = fuzzconfig.FuzzConfig(device, f"extract-site-info-{device}", [])
            config.setup()
            shutil.copyfile(config.udb, udb)

    return run(['des_read_udb "{}"'.format(path.abspath(udb))] + commands, stdout = stdout)

class PipInfo:
    def __init__(self, from_wire, to_wire, is_bidi = False, flags = 0, buffertype = ""):
        self.from_wire = from_wire
        self.to_wire = to_wire
        self.flags = flags
        self.buffertype = buffertype
        self.is_bidi = is_bidi
       
    def __repr__(self):
        return str((self.from_wire, self.to_wire))

class PinInfo:
    def __init__(self, site, pin, wire, pindir):
        self.site = site
        self.pin = pin
        self.wire = wire
        self.dir = pindir

class NodeInfo:
    def __init__(self, name):
        self.name = name
        self.aliases = []
        self.nodetype = None
        self.uphill_pips = []
        self.downhill_pips = []
        self.pins = []
        
    def pips(self):
        return self.uphill_pips + self.downhill_pips
        
node_re = re.compile(r'^\[\s*\d+\]\s*([A-Z0-9a-z_]+)')
alias_node_re = re.compile(r'^\s*Alias name = ([A-Z0-9a-z_]+)')
pip_re = re.compile(r'^([A-Z0-9a-z_]+) (<--|<->|-->) ([A-Z0-9a-z_]+) \(Flags: .+, (\d+)\) \(Buffer: ([A-Z0-9a-z_]+)\)')
pin_re = re.compile(r'^Pin  : ([A-Z0-9a-z_]+)/([A-Z0-9a-z_]+) \(([A-Z0-9a-z_]+)\)')

# Parsing is weird here since the format of the report can vary somewhat.
# Pre 2023; there were no aliases listed and the nodes returned were numbered. Post 2023, each node
# can have a lot of aliases and the only clear indication of which name is normative is its the one
# used in the connections.

def parse_node_report(rpt, node_keys):
    curr_node = None
    nodes_dict = {}
    nodes = []
    reset_curr_node = True
    
    def get_node(name):
        if name in nodes_dict:
            n = nodes_dict[name]
            n.name = name
            return n

        nodes_dict[name] = NodeInfo(name)
        nodes.append(nodes_dict[name])
        return nodes_dict[name]
        
    for line in rpt.split('\n'):
        sl = line.strip()

        name_match = [nm.group(1) for nm in [re.match(sl) for re in [node_re, alias_node_re]] if nm is not None]

        if len(name_match):
            new_name = name_match[0]
            if reset_curr_node:
                curr_node = get_node(new_name)
                reset_curr_node = False
            curr_node.aliases.append(new_name)

            if new_name in node_keys:
                curr_node.name = new_name
            continue

        # If we get back into an alias section, we are onto a new node
        reset_curr_node = True
        
        pm = pip_re.match(sl)
        if pm:
            # Name the node according to what things call it
            curr_node.name = pm.group(1)
            
            flg = int(pm.group(4))
            btyp = pm.group(5)
            #print(f"Found connection {pm}")
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
        #print("Match", qm, curr_node)
        if qm and curr_node:
            curr_node.pins.append(
                PinInfo(qm.group(1), qm.group(2), curr_node.name, qm.group(3))
            )
    #print([x.name for x in nodes])
    return nodes

def parse_sites(rpt):
    past_preamble = False
    sites = []
    for line in rpt.split('\n'):
        sl = line.strip()

        if not past_preamble:
            past_preamble = "Successfully loading udb" in sl
            continue

        if "--------------------" in sl:
            break

        if len(sl):
            sites.append(sl)

    return sites

@cache
def get_full_node_list(udb):
    workdir = f"/tmp/prjoxide_node_data/{udb}"
    nodefile = path.join(workdir, "full_nodes.txt")
    os.makedirs(workdir, exist_ok=True)

    if not os.path.exists(nodefile):
        if not udb.endswith(".udb"):
            config = fuzzconfig.FuzzConfig(udb, "extract-site-info", [])
            config.setup()
            udb = config.udb
        run_with_udb(udb, [f'dev_list_node_by_name -file {nodefile}'])
    with open(nodefile, 'r') as nf:
        return {res for line in nf.read().split("\n")
                if len(res:=line.split(":")[-1].strip()) != 0 }

@cache
def _get_list_arc(device):
    nodefile = f"/tmp/prjoxide_node_data/{device}/arclist"
    if not os.path.exists(nodefile):
        run_with_udb(device, [f'dev_list_arc -file {nodefile} -jumpwire'], stdout=subprocess.DEVNULL)

    with open(nodefile, 'r') as nf:
        nodes = {}
        arcs = set()
        def get_node(n):
            if n not in nodes:
                nodes[n] = NodeInfo(n)
            return nodes[n]

        logging.info(f"Reading arc file {nodefile}")
        for line in nf.readlines():
            parts = line.split(" ")
            if parts[2] != "-->":
                print(line, parts)
            assert parts[2] == "-->"

            pip = PipInfo(parts[1], parts[3])
            get_node(parts[1]).downhill_pips.append(pip)
            get_node(parts[3]).uphill_pips.append(pip)

        for n,info in nodes.items():
            for t in info.pips():
                arcs.add((t.from_wire, t.to_wire))

        return arcs

@cache
def get_jump_wires(device):
    from nodes_database import NodesDatabase
    node_db = NodesDatabase.get(device)
    jmp = set(node_db.get_jumpwires())
    if len(jmp) == 0:
        jmp = _get_list_arc(device)
        node_db.insert_jumpwires(jmp)

    return jmp

@cache
def get_jump_wires_lookup(device):
    rtn = defaultdict(set)
    for jmp in get_jump_wires(device):
        rtn[jmp[0]].add(jmp)
        rtn[jmp[1]].add(jmp)
    return rtn

def get_jump_wires_by_nodes(device, nodes):
    nodes = set(nodes)
    lu = get_jump_wires_lookup(device)

    raw_set = set()
    for n in nodes:
        raw_set = raw_set | lu[n]

    # Most of the things are connections; but sometimes there are multi-source connections. Filter those out.
    raw_dict = defaultdict(list)
    for (from_wire, to_wire) in raw_set:
        raw_dict[to_wire].append(from_wire)

    return {
        (from_wires[0], to_wire)
        for (to_wire, from_wires) in raw_dict.items()
        if len(from_wires) == 1
    }

def _get_node_data(udb, nodes):
    regex = False

    workdir = tempfile.mkdtemp()
    nodefile = path.join(workdir, "nodes.txt")
    nodelist = "[list {}]".format(" ".join(nodes))

    logging.info(f"Querying for {len(nodes)} nodes {nodes[:10]}")

    if not udb.endswith(".udb"):
        device = udb
        udb = f"/tmp/prjoxide_node_data/{device}.udb"
        if not os.path.exists(udb):
            config = fuzzconfig.FuzzConfig(device, f"extract-site-info-{device}", [])
            config.setup()
            shutil.copyfile(config.udb, udb)

    re_slug = "-re " if regex else ""
    run_with_udb(udb, [f'dev_report_node -file {nodefile} [{get_nodes} {re_slug}{nodelist}]'], stdout = subprocess.DEVNULL)

    with open(nodefile, 'r') as nf:
        return parse_node_report(nf.read(), nodes)

async def get_pip_data(device, nodes, filter_type = None):
    from nodes_database import NodesDatabase
    # Make sure we have full db for these entries
    await asyncio.to_thread(get_node_data, device, nodes, skip_pips=True)

    db = NodesDatabase.get(device)
    return db.get_pips(nodes, filter_type = filter_type)

def get_node_data(device, nodes, regex=False, executor = None, filter_by_name=True, skip_missing = False, skip_pips=False):
    from nodes_database import NodesDatabase
    import fuzzloops

    if not isinstance(nodes, (list, set)):
        nodes = [nodes]
    else:
        nodes = sorted(set(nodes))

    if regex:
        all_nodes = get_full_node_list(device)
        regex = [re.compile(n) for n in nodes]
        nodes = sorted(set([n for n in all_nodes if any([r for r in regex if r.search(n) is not None])]))
    elif filter_by_name:
        all_nodes = get_full_node_list(device)
        nodes = sorted(set(nodes) & all_nodes)

    if len(nodes) == 0:
        return []

    db = NodesDatabase.get(device)
    t = time.time()
    nis = db.get_node_data(nodes, skip_pips=skip_pips)
    logging.debug(f"Looked up {len(nis)} records in {time.time() - t} sec")
    missing = sorted({k for k in nodes if k not in nis})
    futures = []

    if not skip_missing and len(missing):
        cnt = 5000
        logging.info(f"Getting from lapie: {len(missing)} nodes {missing[:10]}...")

        with fuzzloops.Executor(executor) as local_executor:
            def lapie_get_node_data(query):
                s = time.time()
                nodes = _get_node_data(device, query)
                logging.debug(f"{len(query)} N {len(query) / (time.time() - s)} N/sec ({(time.time() - s)} deltas)")
                return nodes

            def integrate_nodes(nodes):
                db = NodesDatabase.get(device)
                try:
                    db.insert_nodeinfos(nodes)
                except sqlite3.OperationalError as e:
                    logging.warning(f"Could not populate node db: {e}")

                for n in nodes:
                    nis[n.name] = n

            for grp in itertools.batched(missing, cnt):
                f = local_executor.submit(lapie_get_node_data, list(grp))
                futures.append(fuzzloops.chain(f, integrate_nodes))

    if executor is not None:
        return fuzzloops.chain(futures, lambda _: list(nis.values()))
    else:
        return list(nis.values())

def _get_sites(udb, rc = None):
    rc_slug = ""
    if rc is not None:
        rc_slug = f"-row {rc[0]} -column {rc[1]}"
    rpt = run_with_udb(udb, [f'dev_list_site {rc_slug}'], stdout = subprocess.DEVNULL)

    return parse_sites(rpt)

def get_sites(device, rc = None):
    if rc is None:
        return _get_sites(device, rc)

    sites = get_sites_with_pin(device, rc)
    return list(sites.keys())

def parse_report_site(rpt):
    site_re = re.compile(
        r'^Site=(?P<site_name>\S+)\s+'
        r'id=(?P<id>\d+)\s+'
        r'type=(?P<type>\S+)\s+'
        r'X=(?P<x>-?\d+)\s+'
        r'Y=(?P<y>-?\d+)$'
    )

    pin_re = re.compile(
        r'^\s*Pin\s+id\s*=\s*(?P<pin_id>\d+)\s+'
        r'pin\s+name\s*=\s*(?P<pin_name>\S+)\s+'
        r'pin\s+node\s+name\s*=\s*(?P<pin_node>\S+)$'
    )
    
    past_preamble = False
    sites = {}
    current_site = None
    
    for line in rpt.split('\n'):
        sl = line.strip()

        if not past_preamble:
            past_preamble = "Successfully loading udb" in sl
            continue

        if "--------------------" in sl:
            break

        m = site_re.match(line)
        if m:
            current_site = m.groupdict()
            current_site["pins"] = []
            sites[current_site["site_name"]] = current_site
            del current_site["site_name"]
            
        m = pin_re.match(line)
        if m:
            pins = m.groupdict()
            del pins["pin_id"]
            current_site["pins"].append(pins)

    return sites

@cachecontrol.cache_fn()
def get_sites_with_pin(device):
    from nodes_database import NodesDatabase

    node_db = NodesDatabase.get(device)

    sites = node_db.get_sites()

    if len(sites) == 0:
        rpt = run_with_udb(device, [f'dev_report_site'], stdout = subprocess.DEVNULL)
        sites =  parse_report_site(rpt)

        node_db.insert_sites(sites)

    return sites


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
