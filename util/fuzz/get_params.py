import re, sys

# Read a Lattice Verilog file and extract the parameters and their widths/set of values

ov_re = re.compile(r'\\otherValues = "{([^}]*)}"')
p_re = re.compile(r'parameter ([A-Z0-9a-z_]*) = "([^"]*)"')
# returns [(word_name, word_length)], [(enum_name, [enum_values])]
def get_params(f):
	words = []
	enums = []
	with open(f, "r") as pf:
		other_vals = None
		for line in pf:
			ov_m = ov_re.search(line)
			if ov_m:
				other_vals = ov_m.group(1).split(",")
				if other_vals == [""]:
					other_vals = []
				continue
			p_m = p_re.search(line)
			if p_m:
				name = p_m.group(1)
				val = p_m.group(2)
				if val.startswith("0b"):
					words.append((name, len(val) - 2, val[2:]))
				else:
					assert len(other_vals) > 0
					enums.append((name, [val] + other_vals))
	return (words, enums)

def main():
	words, enums = get_params(sys.argv[1])
	for n, l, d in words:
		print("{}[{}] {}".format(n, l, d))
	for n, v in enums:
		print("{} {{{}}}".format(n, ", ".join(v)))

if __name__ == '__main__':
	main()
