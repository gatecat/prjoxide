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

def rewrite_path(modules, celltype, from_pin, to_pin):
    # Rewrite a (celltype, from_pin, to_pin) tuple given cell data, or returns None to drop the path
    mod = modules["modules"][celltype]
    mod_cells = mod["cells"]

    def get_netid(name):
        if name not in mod["netnames"]:
            return -1
        return mod["netnames"][name]["bits"][0]

    for cellname, cell in mod_cells.items():
        celltype = cell["type"]
        if celltype.startswith("UALUT4"):
            if from_pin in ("A0", "A1", "B0", "B1", "C0", "C1", "D0", "D1") and to_pin in ("F0", "F1"):
                return ("OXIDE_COMB:LUT4", from_pin[0], to_pin[0])
        elif celltype.startswith("UACCU2"):
            if from_pin in ("A0", "A1", "B0", "B1", "C0", "C1", "D0", "D1", "FCI") and to_pin in ("F0", "F1", "FCO"):
                # TODO: split in half?
                return ("OXIDE_COMB:CCU2", from_pin, to_pin)
        elif celltype.startswith("UASLICEREG"):
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
        for dsp_type in dsp_celltypes:
            if not celltype.startswith(dsp_type):
                continue
            def strip_prefix(x):
                for pr in dsp_prefixes:
                    if x.startswith(pr) and x[len(pr):].isdigit():
                        return pr
                return x
            return (dsp_type, strip_prefix(from_pin), strip_prefix(to_pin))
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
                rewritten = rewrite_path(modules, celltype, path.pin, path.clock[1])
                if rewritten is None:
                    continue
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
