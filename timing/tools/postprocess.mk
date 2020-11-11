FOLDER?=output
TOOLS?=tools
UTIL?=util

vo=$(wildcard $(FOLDER)/*.vo)
vo_json=$(patsubst %.vo,%.vo.json,$(vo))

sdf=$(wildcard $(FOLDER)/*.sdf)
sdf_pickled=$(patsubst %.sdf,%.sdf.pickle,$(sdf))

all: $(vo_json) $(sdf_pickled)

%.vo.json: %.vo
	python $(TOOLS)/yosysify_verilog.py $< $<_yosys.v
	yosys -f verilog -p "write_json $@" $<_yosys.v
	rm "$<_yosys.v"

%.sdf.pickle: %.sdf
	python $(TOOLS)/pickle_sdf.py $< $@
