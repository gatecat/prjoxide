#!/usr/bin/env bash
set -ex
for vo in $*; do
	python yosysify_verilog.py $vo ${vo}_yosys.v
	yosys -f verilog -p "write_json ${vo}.json" ${vo}_yosys.v
	rm ${vo}_yosys.v
done
