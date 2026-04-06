#!/bin/bash

radiantdir="${RADIANTDIR:-$HOME/lscc/radiant/3.0}"
export FOUNDRY="${radiantdir}/ispfpga"
bindir="${radiantdir}/bin/lin64"
LSC_DIAMOND=true
export LSC_DIAMOND
export NEOCAD_MAXLINEWIDTH=32767
export TCL_LIBRARY="${radiantdir}/tcltk/linux/lib/tcl8.6"
export fpgabindir=${FOUNDRY}/bin/lin64
ld_lib_path_orig=$LD_LIBRARY_PATH
export LD_LIBRARY_PATH="${bindir}:${fpgabindir}"
export LM_LICENSE_FILE="${radiantdir}/license/license.dat"

#set -ex

V_SUB=${2%.v}
PART=$1
set -- "$1" $V_SUB

EXTRA_BIT_ARGS=

case "${PART}" in
	LIFCL-17)
		PACKAGE="${DEV_PACKAGE:-CABGA256}"
		DEVICE="LIFCL-17"
		LSE_ARCH="lifcl"
		SPEED_GRADE="${SPEED_GRADE:-7_High-Performance_1.0V}"
		;;
	LIFCL-33)
		PACKAGE="${DEV_PACKAGE:-WLCSP84}"
		DEVICE="LIFCL-33"
		LSE_ARCH="lifcl"
		SPEED_GRADE="${SPEED_GRADE:-8_High-Performance_1.0V}"
		;;	
	LIFCL-33U)
		PACKAGE="${DEV_PACKAGE:-FCCSP104}"
		DEVICE="LIFCL-33U"
		LSE_ARCH="lifcl"
		EXTRA_BIT_ARGS="-ipeval"		
		SPEED_GRADE="${SPEED_GRADE:-7_High-Performance_1.0V}"
		;;	
	LIFCL-40)
		PACKAGE="${DEV_PACKAGE:-CABGA400}"
		DEVICE="LIFCL-40"
		LSE_ARCH="lifcl"
		SPEED_GRADE="${SPEED_GRADE:-7_High-Performance_1.0V}"
		;;
	LFD2NX-40)
		PACKAGE="${DEV_PACKAGE:-CABGA256}"
		DEVICE="LFD2NX-40"
		LSE_ARCH="lfd2nx"
		SPEED_GRADE="${SPEED_GRADE:-7_High-Performance_1.0V}"
		;;
	LFCPNX-100)
		PACKAGE="${DEV_PACKAGE:-LFG672}"
		DEVICE="LFCPNX-100"
		LSE_ARCH="lfcpnx"
		EXTRA_BIT_ARGS="-ipeval"
		SPEED_GRADE="${SPEED_GRADE:-7_High-Performance_1.0V}"
		;;
esac

SCRIPT_PATH=$(readlink -f "${BASH_SOURCE:-$0}")
SCRIPT_DIR=$(dirname "$SCRIPT_PATH")
bscache=${BITSTREAM_CACHE:-$SCRIPT_DIR/tools/bitstreamcache.py}

(

rm -rf "$2.tmp"
mkdir -p "$2.tmp"
cp "$2.v" "$2.tmp/input.v"
MAYBE_PDC=""
if [ -e "$2.pdc" ]; then cp "$2.pdc" "$2.tmp/input.pdc"; MAYBE_PDC="$2.tmp/input.pdc"; fi

if ([ -z "$FORCE_REBUILD"] && (LD_LIBRARY_PATH=$ld_lib_path_orig $bscache fetch $PART "$2.tmp" "$2.tmp/input.v" $MAYBE_PDC)); then
	# Cache hit
	echo "Cache hit, not running Radiant"
else
	# Cache miss
	cd "$2.tmp"
	if [ -n "$STRUCT_VER" ]; then
	  rm -f par.udb
	"$fpgabindir"/sv2udb -o par.udb input.v
	else
	"$fpgabindir"/synthesis -a "$LSE_ARCH" -p "$DEVICE" -t "$PACKAGE" \
				-use_io_insertion 1 -use_io_reg auto -use_carry_chain 1 \
				-ver input.v \
				-output_hdl synth.vm

	"$fpgabindir"/postsyn -a "$LSE_ARCH" -p "$DEVICE" -t "$PACKAGE" -sp "$SPEED_GRADE" \
				-top -w -o synth.udb synth.vm
	if [ -e input.pdc ]; then
		MAP_PDC="input.pdc"
	else
		MAP_PDC=""
	fi
	"$fpgabindir"/map -o map.udb synth.udb $MAP_PDC
	"$fpgabindir"/par map.udb -w par.udb
	fi

	if [ -n "$GEN_RBF" ]; then
		OUTPUT=$("$fpgabindir"/bitgen $EXTRA_BIT_ARGS -b -d -w par.udb 2>&1)
		if [[ $OUTPUT == *"ERROR <"* ]]; then
		  echo "Exiting due to error found during bitgen"
		  exit -1
		fi

		LD_LIBRARY_PATH=$ld_lib_path_orig $bscache commit $PART "input.v" $MAP_PDC output "par.udb" "par.rbt"
	else
		if [ -n "$RBK_MODE" ]; then
			OUTPUT=$("$fpgabindir"/bitgen $EXTRA_BIT_ARGS -d -w -m 1 par.udb 2>&1)
			mv par.rbk par.bit
		else	
			OUTPUT=$("$fpgabindir"/bitgen $EXTRA_BIT_ARGS -d -w par.udb 2>&1)
		fi

			if [[ $OUTPUT == *"ERROR <"* ]]; then
			   echo "Exiting due to error found during bitgen"
			   exit -1
		  fi

		LD_LIBRARY_PATH=$ld_lib_path_orig $bscache commit $PART "input.v" $MAP_PDC output "par.udb" "par.bit"
	fi
	export LD_LIBRARY_PATH=""
fi
)

if [ -n "$GEN_RBF" ]; then
cp "$2.tmp"/par.rbt "$2.rbt"
else
cp -P "$2.tmp"/par.bit "$2.bit" 2> /dev/null || :
cp -P "$2.tmp"/par.bit.gz "$2.bit.gz" 2> /dev/null || :
fi

if [ -n "$DO_UNPACK" ]; then
prjoxide unpack "$2.bit" "$2.fasm"
fi
