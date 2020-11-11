import random

# Some representative pins for each bank

bank_pins = {
    0: ("E12", "E13", "D13", "D15", "D14", "D16"),
    1: ("F13", "F16", "F18", "E20", "G18", "G14", "L13", "L16", "L20"),
    2: ("N14", "M16", "N15", "M19", "N19", "P19", "P17", "R17", "U20"),
    3: ("W18", "Y17", "V17", "U15", "Y15", "P13", "V14", "Y13", "R12", "U12", "W13", "V11"),
    4: ("U10", "T10", "W9", "W8", "P10", "Y7", "R8", "P7", "W7", "W6", "V6"),
    5: ("Y2", "R5", "Y5"),
    6: ("R3", "P5", "P2", "N7", "N6", "N5", "N4", "M7", "M6", "M5", "M4", "M3", "M2", "L8"),
    7: ("K1", "K2", "J2", "E2", "E3", "E4", "E7", "E8", "E9", "E10", "D3", "D4", "D5", "D6", "D7")
}

io33_types = [
    ("LVCMOS10", 1.2, ["INPUT"]),
    ("LVCMOS12", 1.2, None),
    ("LVCMOS15", 1.5, None),
    ("LVCMOS18", 1.8, None),
    ("LVCMOS25", 2.5, None),
    ("LVCMOS33", 3.3, None),
]

io18_types = [
    ("LVCMOS18H", 1.8, None),
    ("LVCMOS15H", 1.5, None),
    ("LVCMOS12H", 1.2, None),
    ("LVCMOS10H", 1.0, None),
    ("LVCMOS10R", 1.8, ["INPUT"]),
    ("SSTL135_I", 1.35, None),
#    ("SSTL135_II", 1.35, None),
    ("SSTL15_I", 1.5, None),
#    ("SSTL15_II", 1.5, None),
    ("HSTL15_I", 1.5, None),
    ("HSUL12", 1.2, None),
    ("LVDS", 1.8, None),
    ("SUBLVDS", 1.8, ["INPUT"]),
#    ("SUBLVDSEH", 1.8, ["OUTPUT"]),
    ("SLVS", 1.2, ["INPUT"]),
#    ("MIPI_DPHY", 1.2, None),
    ("SSTL135D_I", 1.35, None),
#    ("SSTL135D_II", 1.35, None),
    ("SSTL15D_I", 1.5, None),
#    ("SSTL15D_II", 1.5, None),
    ("HSTL15D_I", 1.5, None),
    ("HSUL12D", 1.2, None),
]

io33_vcc = [3.3, 2.5, 1.8, 1.5, 1.2]
io18_vcc = [1.8, 1.5, 1.35, 1.2, 1.0]

slew_settings = ["SLOW", "MED", "FAST"]

drive_settings = {
    "LVCMOS33": ["2", "4", "8", "12", "50RS"],
    "LVCMOS25": ["2", "4", "8", "10", "50RS"],
    "LVCMOS18": ["2", "4", "8", "50RS"],
    "LVCMOS15": ["2", "4"],
    "LVCMOS12": ["2", "4"],
    "LVCMOS18H": ["2", "4", "8", "12", "50RS"],
    "LVCMOS15H": ["2", "4", "8"],
    "LVCMOS12H": ["2", "4", "8"],
    "LVSMOS10H": ["2", "4"],
    "HSUL12": ["4", "8"],
}

diff_types = ("LVDS", "SUBLVDS", "SUBLVDSEH", "SLVS", "MIPI_DPHY", "SSTL15D_I", "SSTL15D_II", "SSTL135D_I", "SSTL135D_II", "HSTL15D_I", "HSUL12D")

def main():
    # Pick a random Vcc for each bank
    bank_vcc = {}
    for bank in sorted(bank_pins.keys()):
        if bank in (3, 4, 5):
            bank_vcc[bank] = random.choice(io18_vcc)
        else:
            bank_vcc[bank] = random.choice(io33_vcc)
    # Pick settings for each pin
    pin_settings = {}
    pin2bank = {}

    def get_iotype(bank, force_output=False):
        while True:
            iotype, vcc, iodirs = random.choice(io18_types if bank in (3, 4, 5) else io33_types)
            if force_output and iodirs is not None and "OUTPUT" not in iodirs:
                continue
            if vcc == bank_vcc[bank]:
                return (iotype, vcc, iodirs) 

    for bank, pins in sorted(bank_pins.items()):
        for pin in pins:
            pin2bank[pin] = bank
            # Pick a compatible type
            iotype, vcc, iodirs = get_iotype(bank)
            # Pick a compatible direction
            iodir = random.choice(iodirs if iodirs is not None else ["INPUT", "OUTPUT", "INOUT"])
            # Pick extra settings (drive and slew rate)
            extra_cfg = []
            if iodir in ("OUTPUT", "INOUT"):
                if iotype in drive_settings:
                    extra_cfg.append(("DRIVE", random.choice(drive_settings[iotype])))
                if iotype in diff_types:
                    pass
                elif "SSTL" in iotype or "HSUL" in iotype or "HSTL" in iotype:
                    extra_cfg.append(("SLEWRATE", random.choice(slew_settings[1:])))
                else:
                    extra_cfg.append(("SLEWRATE", random.choice(slew_settings)))
            pin_settings[pin] = (iotype, iodir, extra_cfg)
    io_names = {}
    print("module top (")
    for pin, setting in sorted(pin_settings.items()):
        # Encode config in pin name so we can parse it later on
        io_name = "{}__{}__{}{}".format(
            pin, setting[0], setting[1], "".join("__{}_{}".format(k, v) for k, v in setting[2])
        )
        print('    (* LOC="{}", IO_TYPE="{}"{} *)'.format(
            pin, setting[0], "".join(', {}="{}"'.format(k, v) for k, v in setting[2])
        ))
        print('    {} {},'.format(setting[1].lower(), io_name))
        io_names[pin] = io_name
    print('    (* IO_TYPE="{}" *) input [6:0] d,'.format(get_iotype(6)[0]))
    print('    (* IO_TYPE="{}" *) input sclk,'.format(get_iotype(2)[0]))
    for b in (3, 4, 5):
        print('    (* IO_TYPE="{}" *) input eclk{},'.format(get_iotype(b)[0], b))
    print('    (* IO_TYPE="{}" *) output q'.format(get_iotype(2, force_output=True)[0]))
    print(");")

    output_count = 0

    def i():
        return "d[{}]".format(random.randint(0, 3))
    def o():
        nonlocal output_count
        sig = "o[{}]".format(output_count)
        output_count += 1
        return sig

    # Edge clock dividers
    print("    wire sclk3, sclk4, sclk5;")
    bank_rates = {}
    for bank in (3, 4, 5):
        # TODO: 3.5
        rate = random.choice([2, 4, 5])
        bank_rates[bank] = rate
        print('    ECLKDIV_CORE #(')
        print('        .ECLK_DIV("{}")'.format(rate))
        print('    ) ediv_{} ('.format(bank))
        print('         .ECLKIN(eclk{}),'.format(bank))
        print('         .DIVOUT(sclk{})'.format(bank))
        print('    );')

    # IO buffer, delay and IOLOGIC
    for pin, setting in sorted(pin_settings.items()):
        sig_i = "{}_i".format(pin)
        sig_t = "{}_t".format(pin)
        sig_o = "{}_o".format(pin)
        iotye, d, extra_args = setting
        print("    wire {};".format(", ".join((sig_i, sig_o, sig_t))))

        bank = pin2bank[pin]
        # Encode in name for the IOLOGIC cell timing fuzzer
        iobt = "__IOB_" if bank in (3, 4, 5) else "_S_IOB"

        # IO buffer
        if d == "INPUT":
            print("    IB {p}{s}_b (.I({n}), .O({p}_o));".format(p=pin, s=iobt, n=io_names[pin]))
            sig_t = None
            sig_i = None
        elif d == "OUTPUT":
            print("    OB {p}{s}_b (.O({n}), .I({p}_i));".format(p=pin, s=iobt, n=io_names[pin]))
            sig_o = None
        elif d == "INOUT":
            print("    BB {p}{s}_b (.B({n}), .I({p}_i), .T({p}_t), .O({p}_o));".format(p=pin, s=iobt, n=io_names[pin]))

        # Delay
        def delaya_common():
            print("         .LOAD_N(!d[4]),")
            print("         .MOVE(!d[5]),")
            print("         .DIRECTION(!d[6]),")
            print("         .CFLAG({}),".format(o()))

        od_used = False

        if d in ("INPUT", "INOUT") and random.random() < 0.15:
            print("    wire {}_od;".format(pin))
            if pin2bank[pin] in (3, 4, 5):
                print("    DELAYA {}_del (".format(pin))
                print("         .A({}_o),".format(pin))
                delaya_common()
                print("         .Z({}_od)".format(pin))
                print("    );")
            else:
                print("    DELAYB {}_del (".format(pin))
                print("         .A({}_o),".format(pin))
                print("         .Z({}_od)".format(pin))
                print("    );")
            sig_o = "{}_od".format(pin)
        elif d in ("OUTPUT", "INOUT") and random.random() < 0.15:
            od_used = True
            print("    wire {}_id;".format(pin))
            if pin2bank[pin] in (3, 4, 5):
                print("    DELAYA {}_del (".format(pin))
                print("         .A({}_id),".format(pin))
                delaya_common()
                print("         .Z({}_i)".format(pin))
                print("    );")
            else:
                print("    DELAYB {}_del (".format(pin))
                print("         .A({}_id),".format(pin))
                print("         .Z({}_i)".format(pin))
                print("    );")
            sig_i = "{}_id".format(pin)

        # IOLOGIC
        rate = bank_rates.get(bank, 0)
        iol_types = []
        if d in ("INPUT", "INOUT"):
            iol_types.append("IREG")
            iol_types.append("IDDR")
        if d in ("INOUT", "OUTPUT"):
            iol_types.append("OREG")
            iol_types.append("ODDR")
        if d == "INPUT" and rate != 0: iol_types.append("IDDRN")
        if d == "OUTPUT" and rate != 0: iol_types.append("ODDRN")

        if random.random() > 0.5:
            iol = random.choice(iol_types)
            if iol == "IREG":
                print("    {prim} {p}_ireg (.CK(sclk), .D({io_o}), .SP({sp}), .CD({cd}), .Q({q}));".format(
                    prim=random.choice(["IFD1P3DX", "IFD1P3IX"]),
                    p=pin, io_o=sig_o, sp=i(), cd=i(), q=o(),
                ))
                sig_o = None
            elif iol == "OREG":
                prim = random.choice(["OFD1P3DX", "OFD1P3IX"])
                sp = i()
                cd = i()
                print("    {prim} {p}_oreg (.CK(sclk), .D({d}), .SP({sp}), .CD({cd}), .Q({io_i}));".format(
                    prim=prim, p=pin, d=i(), sp=sp, cd=cd, io_i=sig_i,
                ))
                sig_i = None
                if sig_t is not None and random.random() > 0.5:
                    print("    {prim} {p}_treg (.CK(sclk), .D({t}), .SP({sp}), .CD({cd}), .Q({io_t}));".format(
                        prim=prim, p=pin, t=i(), sp=sp, cd=cd, io_t=sig_t,
                    ))
                    sig_t = None
            elif iol == "IDDR":
                print("    IDDRX1 {p}_iddr (.SCLK(sclk), .D({io_o}), .RST({rst}), .Q0({q0}), .Q1({q1}));".format(
                    p=pin, io_o=sig_o, rst=i(), q0=o(), q1=o(),
                ))
                sig_o=None
            elif iol == "ODDR":
                print("    ODDRX1 {p}_oddr (.SCLK(sclk), .D0({d0}), .D1({d1}), .RST({rst}), .Q({io_i}));".format(
                    p=pin, d0=i(), d1=i(), rst=i(), io_i=sig_i,
                ))
                sig_i=None
            elif iol == "IDDRN":
                print("    IDDRX{n} {p}_iddr (.SCLK(sclk{b}), .ECLK(eclk{b}), .D({io_o}), .RST({rst}), .ALIGNWD({aw}), {q});".format(
                    n=rate, p=pin, b=bank, io_o=sig_o, rst=i(), aw=i(),
                    q=", ".join(".Q{}({})".format(j, o()) for j in range(2*rate))
                ))
                sig_o=None
            elif iol == "ODDRN":
                print("    ODDRX{n} {p}_iddr (.SCLK(sclk{b}), .ECLK(eclk{b}), .Q({io_i}), .RST({rst}), {d});".format(
                    n=rate, p=pin, b=bank, io_i=sig_i, rst=i(),
                    d=", ".join(".D{}({})".format(j, i()) for j in range(2*rate))
                ))
                sig_i=None
            else:
                assert False
        if sig_i is not None:
            print("    assign {} = {}{};".format(sig_i, "!" if od_used else "", i()))
        if sig_t is not None:
            print("    assign {} = {};".format(sig_t, i()))
        if sig_o is not None:
            print("    assign {} = {};".format(o(), sig_o))
        print()

    print("    wire [{}:0] o;".format(output_count-1))
    print("    assign q = ^o;")
    print("endmodule")

if __name__ == '__main__':
    main()
