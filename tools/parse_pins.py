import json, sys

# Parse a Lattice pinout CSV file to a JSON file for the database
# Usage: parse_pins.py pinout.csv iodb.json

def main():
	packages = []
	pads = []
	with open(sys.argv[1], "r") as csvf:
		for line in csvf:
			sl = line.replace('"', '')
			sl = sl.strip()
			if len(sl) == 0 or sl.startswith('#'):
				continue
			splitl = [x.strip() for x in sl.split(',')]
			if len(splitl) == 0 or splitl[0] == '':
				continue
			if len(packages) == 0:
				# Header line
				COL_PADN = splitl.index("PADN")
				COL_FUNC = splitl.index("Pin/Ball Funcion")
				COL_CUST_NAME = splitl.index("CUST_NAME") if "CUST_NAME" in splitl else None
				COL_BANK = splitl.index("BANK")
				COL_DF = splitl.index("Dual Function")
				COL_LVDS = splitl.index("LVDS")
				COL_HIGHSPEED = splitl.index("HIGHSPEED")
				COL_DQS =  splitl.index("DQS") if "DQS" in splitl else None
				COL_PKG_START = 1 + max(x for x in [COL_PADN, COL_FUNC, COL_CUST_NAME, COL_BANK, COL_DF, COL_LVDS, COL_HIGHSPEED, COL_DQS] if x is not None)

				packages = splitl[COL_PKG_START:]
				continue
			func = splitl[COL_FUNC]
			io_offset = -1
			io_side = ''
			io_spfunc = []
			io_pio = -1
			io_dqs = []
			io_vref = -1
			if len(func) >= 4 and func[0] == 'P' and func[1] in ('T', 'L', 'R', 'B') and func[-1] in ('A', 'B', 'C', 'D') and "_" not in func:
				# Regular PIO
				io_offset = int(func[2:-1])
				io_side = func[1]
				io_spfunc = splitl[COL_DF].split('/')
				io_pio = "ABCD".index(func[-1])
				if io_spfunc == ['-']:
					io_spfunc = []
				io_dqs = splitl[COL_DQS] if COL_DQS is not None else ""
				if io_dqs == "" or io_dqs == "-":
					io_dqs = []
				elif io_dqs.find("DQSN") == 1:
					io_dqs = [2, int(io_dqs[5:])]
				elif io_dqs.find("DQS") == 1:
					io_dqs = [1, int(io_dqs[4:])]
				elif io_dqs.find("DQ") == 1:
					io_dqs = [0, int(io_dqs[3:])]
				else:
					print(f"Bad DQS type {io_dqs}")
					assert False, "bad DQS type"

				for spf in io_spfunc:
					if spf.startswith('VREF'):
						bank, _, ref = spf[4:].partition('_')
						assert int(bank) == int(splitl[COL_BANK])
						io_vref = int(ref)

			elif func.startswith('ADC_') or func.startswith('DPHY') or func.startswith('SD0') or func.startswith('JTAG_'):
				# Special IO, that we still want in the db
				io_spfunc = [func, ]
			else:
				continue
			io_bank = int(splitl[COL_BANK]) if splitl[COL_BANK].isdigit() else -1
			io_pins = splitl[COL_PKG_START:]
			pads.append(dict(side=io_side, offset=io_offset, pio=io_pio, func=io_spfunc, bank=io_bank, dqs=io_dqs, vref=io_vref, pins=io_pins))
	with open(sys.argv[2], "w") as jsf:
		jsf.write(json.dumps(dict(packages=packages, pads=pads), sort_keys=True, indent=4))
		jsf.write('\n')
if __name__ == '__main__':
	main()
