# Common Makefile for Nexus examples

SYNTH_ARGS=-flatten

YOSYS?=yosys
NEXTPNR?=nextpnr-nexus
PRJOXIDE?=prjoxide
ECPPROG?=ecpprog
TOP?=top

all: $(PROJ).bit

$(PROJ).json: $(PROJ).v $(EXTRA_VERILOG) $(MEM_INIT_FILES) 
	$(YOSYS) -l $(PROJ)_syn.log -DSYNTHESIS=1 -p "synth_nexus $(SYNTH_ARGS) -top $(TOP) -json $(PROJ).json" $(PROJ).v $(EXTRA_VERILOG)

$(PROJ).fasm: $(PROJ).json $(PDC)
	$(NEXTPNR) --device $(DEVICE) --pdc $(PDC) --sdc $(SDC) --json $(PROJ).json --fasm $(PROJ).fasm --report $(PROJ).report --detailed-timing-report -l $(PROJ)_par.log

$(PROJ).bit: $(PROJ).fasm
	$(PRJOXIDE) pack $(PROJ).fasm $(PROJ).bit

prog: $(PROJ).bit
	$(ECPPROG) -S $(PROJ).bit

prog-flash: $(PROJ).bit
	$(ECPPROG) $(PROJ).bit

clean:
	rm -f $(PROJ).json $(PROJ).fasm $(PROJ)_syn.log $(PROJ).bit

.SECONDARY:
.PHONY: prog prog-flash clean
