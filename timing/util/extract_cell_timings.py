from parse_sdf import parse_sdf_file, IOPath
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
            ffinst = modules["modules"][celltype]["cells"]["INST10"]
            synctype = "ASYNC" if ffinst["parameters"].get("ASYNC", "NO") == "YES" else "SYNC"
            return ("OXIDE_FF:{}:{}".format(invstr, synctype), from_pin, to_pin)
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
                from_port = path.from_pin[1] if isinstance(path.from_pin, tuple) else path.from_pin
                rewritten = rewrite_path(modules, celltype, from_port, path.to_pin)
                if rewritten is None:
                    continue
                paths.add((rewritten[0], rewritten[1], rewritten[2],
                    min(path.rising.minv, path.falling.minv),
                    max(path.rising.typv, path.falling.typv),
                    max(path.rising.maxv, path.falling.maxv),
                ))

    for path in sorted(paths):
        print("{:60s} {:10s} {:10s} {:4d} {:4d} {:4d}".format(*path))

if __name__ == '__main__':
    main()
