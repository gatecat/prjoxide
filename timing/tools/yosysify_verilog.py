import sys

in_spec = False

with open(sys.argv[1], "r") as i:
	with open(sys.argv[2], "w") as o:
		for line in i:
			if " specify" in line or in_spec:
				if " endspecify" in line:
					in_spec = False
				else:
					in_spec = True
				continue # Yosys can't cope with the more complex features used
			o.write(line)
