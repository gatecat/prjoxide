from parse_sdf import parse_sdf_file, IOPath, SetupHoldCheck
import sys, json

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

# DSP cell types
dsp_celltypes = {
    "MULT9_CORE",
    "PREADD9_CORE",
    "MULT18_CORE",
    "REG18_CORE",
    "MULT18X36_CORE",
    "MULT36_CORE",
    "ACC54_CORE",
}

ebr_celltypes = {
    "SP16K_MODE",
    "DP16K_MODE",
    "PDP16K_MODE",
    "PDPSC16K_MODE",
    "FIFO16K_MODE",
}

# We strip off these prefices, as all delays to 'subports' are the same
dsp_prefixes = [
    "M9ADDSUB", "ADDSUB",
    "SFTCTRL", "DSPIN", "CINPUT", "DSPOUT", "CASCOUT", "CASCIN",
    "PML72", "PMH72", "SUM1", "SUM0",
    "BRS1", "BRS2", "BLS1", "BLS2", "BLSO", "BRSO", "PL18", "PH18", "PL36", "PH36", "PL72", "PH72",
    "P72", "P36", "P18", "AS1", "AS2", "ARL", "ARH", "BRL", "BRH",
    "AO", "BO", "AB", "AR", "BR", "PM", "PP",
    "A", "B", "C",
]
ebr_prefixes = [
    "DIA",
    "DIB",
    "DOA",
    "DOB",
    "CSA",
    "CSB",
    "ADA",
    "ADB",
]

# Which IOLOGIC signals are relevant for which purposes...
iol_input_sigs = ["SCLKIN", "CEIN", "LSRIN", "INFF", "DI", "WORDALIGN"] + ["RXDATA{}".format(i) for i in range(10)]
iol_output_sigs = ["SCLKOUT", "CEOUT", "LSROUT", "DOUT", "TOUT"] + ["TXDATA{}".format(i) for i in range(10)] + ["TSDATA{}".format(i) for i in range(4)]
iol_dly_sigs = ["INDD", "DIR", "LOAD_N", "MOVE", "CFLAG"]

def rewrite_path(modules, modtype, from_pin, to_pin):
    # Rewrite a (celltype, from_pin, to_pin) tuple given cell data, or returns None to drop the path
    # This looks at the JSON output by Yosys from the Lattice structural Verilog netlist in order
    # to determine what the cells in the SDF file are actually doing
    mod = modules["modules"][modtype]
    mod_cells = mod["cells"]

    def get_netid(name):
        if name not in mod["netnames"]:
            return -1
        return mod["netnames"][name]["bits"][0]

    for cellname, cell in mod_cells.items():
        # Go through each sub-cell inside the SDF-level cell module
        celltype = cell["type"]
        if celltype.startswith("UALUT4"):
            # Simple LUT4s
            if from_pin in ("A0", "A1", "B0", "B1", "C0", "C1", "D0", "D1") and to_pin in ("F0", "F1"):
                return ("OXIDE_COMB:LUT4", from_pin[0], to_pin[0])
        elif celltype.startswith("UACCU2"):
            # Carries
            if from_pin in ("A0", "A1", "B0", "B1", "C0", "C1", "D0", "D1", "FCI") and to_pin in ("F0", "F1", "FCO"):
                # TODO: split in half?
                return ("OXIDE_COMB:CCU2", from_pin, to_pin)
        elif celltype.startswith("UASLICEREG"):
            # Flipflops
            # We need to work if we are index 0 or 1 within the SLICE, use the connectivity of Q1 to determine this
            idx = 1 if cell["connections"]["Q"][0] == get_netid("Q1") else 0
            if from_pin in ("DI0", "DI1", "M0", "M1"):
                if int(from_pin[-1]) != idx:
                    continue
                from_pin = from_pin[:-1]
            elif from_pin not in ("LSR", "CE", "CLK"):
                continue
            if to_pin in ("Q0", "Q1"):
                if int(to_pin[-1]) != idx:
                    continue
                to_pin = to_pin[:-1]
            elif to_pin != "CLK":
                continue
            invstr = "N" if "CLK_INVERTERIN" in mod_cells else "P"
            invstr += "N" if "LSR_INVERTERIN" in mod_cells else "P"
            invstr += "N" if "CE_INVERTERIN" in mod_cells else "P"

            # Skip these, as they aren't actually different numerically so we can derive them later on and just clutter things up
            if invstr != "PPP":
                return None
            ffinst = modules["modules"][celltype]["cells"]["INST10"]
            synctype = "ASYNC" if ffinst["parameters"].get("ASYNC", "NO") == "YES" else "SYNC"
            return ("OXIDE_FF:{}:{}".format(invstr, synctype), from_pin, to_pin)
        elif "_INPUT" in modtype or "_OUTPUT" in modtype or "_INOUT" in modtype:
            # PIO config is encoded in name
            ct = modtype.split("__")
            new_type = "PIO:{}{}".format(
                ct[1], "".join(":{}".format(kv) for kv in ct[3:]) 
            )
            if "_INPUT" in from_pin or "_OUTPUT" in from_pin or "_INOUT" in from_pin:
                from_pin = "IOPAD"
            if "_INPUT" in to_pin or "_OUTPUT" in to_pin or "_INOUT" in to_pin:
                to_pin = "IOPAD"
            return (new_type, from_pin, to_pin)
        if "_S_IOB_" in modtype or "__IOB_" in modtype:

            def idelay_used():
                di_idx = get_netid("DI")
                for cellname2, cell2 in mod_cells.items():
                    if cell2["type"].startswith("DELAY") and cell2["connections"]["A"][0] == di_idx:
                        return True
                return False
            def odelay_used():
                dout_idx = get_netid("DOUT")
                for cellname2, cell2 in mod_cells.items():
                    if cell2["type"].startswith("DELAY") and cell2["connections"]["Z"][0] == dout_idx:
                        return True
                return False
            # For IOLOGIC, we encode in the buffer name (which becomes the IOL name)
            # whether this is a simple 'SIOLOGIC' or full 'IOLOGIC'
            s = "S" if "_S_IOB_" in modtype else ""
            if celltype.startswith("DELAY"):
                if from_pin in iol_dly_sigs or to_pin in iol_dly_sigs:
                    return ("{}IOLOGIC:DELAY".format(s), from_pin, to_pin)
            elif celltype.startswith("IOREG"):
                if from_pin in iol_input_sigs or to_pin in iol_input_sigs:
                    return ("{}IOLOGIC:IREG{}".format(s, ":DELAYED" if idelay_used() else ""), from_pin, to_pin)
                if from_pin in iol_output_sigs or to_pin in iol_output_sigs:
                    return ("{}IOLOGIC:OREG{}".format(s, ":DELAYED" if odelay_used() else ""), from_pin, to_pin)
            elif celltype.startswith("IDDR"):
                ddrtype = celltype[:6]
                if from_pin in iol_input_sigs or to_pin in iol_input_sigs:
                    if to_pin[-1].isdigit():
                        to_pin = to_pin[:-1]
                    return ("{}IOLOGIC:{}{}".format(s, ddrtype, ":DELAYED" if idelay_used() else ""), from_pin, to_pin)
            elif celltype.startswith("ODDR"):
                ddrtype = celltype[:6]
                if from_pin in iol_output_sigs or to_pin in iol_output_sigs:
                    if from_pin[-1].isdigit():
                        from_pin = from_pin[:-1]
                    return ("{}IOLOGIC:{}{}".format(s, ddrtype, ":DELAYED" if odelay_used() else ""), from_pin, to_pin)
        # Removing prefices as defined above; for buses that share delays
        def strip_prefix(x, p):
            for pr in p:
                if x.startswith(pr) and x[len(pr):].isdigit():
                    return pr
            return x
        def strip_prefix_ebr(x, p):
            for pr in p:
                if x.startswith(pr) and x[len(pr):].isdigit():
                    pin = pr
                    if pr in ("ADA", "ADB"):
                        i = int(x[len(pr):])
                        pin += "_13_5" if i > 4 else "_4_0"
                    return pin
            return x
        # Handle the special cases of DSP and EBR
        for dsp_type in dsp_celltypes:
            if not celltype.startswith(dsp_type):
                continue
            return (dsp_type, strip_prefix(from_pin, dsp_prefixes), strip_prefix(to_pin, dsp_prefixes))
        for ebr_type in ebr_celltypes:
            if not celltype.startswith(ebr_type):
                continue
            return (ebr_type, strip_prefix_ebr(from_pin, ebr_prefixes), strip_prefix_ebr(to_pin, ebr_prefixes))
    return None

def main():
    with open(sys.argv[1], "r") as jf:
        modules = json.load(jf)
    sdf = parse_sdf_file(sys.argv[2])
    paths = set()
    for cell in sdf.cells.values():
        celltype = unescape_sdf_name(cell.type)
        for path in cell.entries:
            if isinstance(path, IOPath):
                rewritten = rewrite_path(modules, celltype, path.from_pin, path.to_pin)
                if rewritten is None:
                    continue
                paths.add((
                    rewritten[0],
                    "IOPath",
                    rewritten[1],
                    rewritten[2],
                    path.rising.minv, path.rising.typv, path.rising.maxv,
                    path.falling.minv, path.falling.typv, path.falling.maxv,
                ))
            elif isinstance(path, SetupHoldCheck):
                pin = path.pin
                if isinstance(path.pin, list):
                    pin = pin[1]
                rewritten = rewrite_path(modules, celltype, pin, path.clock[1])
                if rewritten is None:
                    continue
                if isinstance(path.pin, list):
                    pin = "({}, {})".format(path.pin[0], rewritten[1])
                else:
                    pin = rewritten[1]
                paths.add((
                    rewritten[0],
                    "SetupHold",
                    rewritten[1],
                    "({}, {})".format(path.clock[0], rewritten[2]),
                    path.setup.minv, path.setup.typv, path.setup.maxv,
                    path.hold.minv, path.hold.typv, path.hold.maxv,
                ))
    for path in sorted(paths):
        print("{:40s} {:10s} {:20s} {:20s} {:4d} {:4d} {:4d} {:4d} {:4d} {:4d}".format(*path))

if __name__ == '__main__':
    main()
