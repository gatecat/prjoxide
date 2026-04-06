from fuzzconfig import FuzzConfig
import nonrouting
from interconnect import fuzz_interconnect
import lapie
import re
import fuzzloops

configs = [
    ((46, 6), FuzzConfig(job="CIBENABLE", device="LIFCL-40", sv="../shared/route_40.v", tiles=["CIB_R46C6:CIB"])),
    ((1, 18), FuzzConfig(job="CIBTENABLE", device="LIFCL-40", sv="../shared/route_40.v", tiles=["CIB_R1C18:CIB_T"])),
    ((23, 86), FuzzConfig(job="CIBLRENABLE", device="LIFCL-40", sv="../shared/route_40.v", tiles=["CIB_R23C86:CIB_LR"])),
    ((37, 86), FuzzConfig(job="CIBLRAENABLE", device="LIFCL-40", sv="../shared/route_40.v", tiles=["CIB_R37C86:CIB_LR_A", "CIB_R38C86:CIB_LR_B"])),
]

def main(executor):
    def per_cib(cib):
        rc, cfg = cib
        cfg.setup()
        empty = cfg.build_design(cfg.sv, {})
        r, c = rc
        # CIB F/Q "used" bits
        nodes = ["R{}C{}_JF{}".format(r, c, i) for i in range(8)]
        nodes += ["R{}C{}_JQ{}".format(r, c, i) for i in range(8)]

        node_data = lapie.get_node_data(cfg.device, nodes)
        for n in node_data:
            to_wire = n.name
            setting_name = to_wire.split("_")[1] + "_USED"
            from_wire = None
            for p in n.uphill_pips:
                if "CIBTEST" not in p.from_wire:
                    from_wire = p.from_wire
                    break
            assert from_wire is not None
            arcs_attr = r', \dm:arcs ="{}.{}"'.format(to_wire, from_wire)
            nonrouting.fuzz_enum_setting(cfg, empty, "CIB." + setting_name, ["NO", "YES"],
                    lambda x: dict(arcs_attr=arcs_attr) if x == "YES" else {}, False, executor=executor)

        # # CIBMUXIN -> CIBMUXOUT
        # cfg.sv = "cib_iomux_40.v"
        # for x in ("A", "B", "C", "D"):
        #     # Stop Radiant trying to tie unused outputs; as this causes weird bit patterns
        #     extra_arcs = []
        #     for i in range(8):
        #         for x2 in ("A", "B", "C", "D"):
        #             if x2 == x:
        #                 continue
        #             extra_arcs.append("R{r}C{c}_JCIBMUXOUT{x}{i}.R{r}C{c}_JCIBMUXINA{i}".format(r=r, c=c, x=x2, i=i))
        #     cibmuxout = ["R{}C{}_JCIBMUXOUT{}{}".format(r, c, x, i) for i in range(8)]
        #     fuzz_interconnect(config=cfg, nodenames=cibmuxout, regex=False, bidir=False, full_mux_style=True,
        #         extra_substs=dict(extra_arc=" ".join(extra_arcs)), executor=executor)
    fuzzloops.parallel_foreach(configs, per_cib)

if __name__ == "__main__":
    fuzzloops.FuzzerMain(main)
