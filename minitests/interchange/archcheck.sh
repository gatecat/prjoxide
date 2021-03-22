#!/usr/bin/env bash
set -ex

# TODO: make these configurable
DEVICE=LIFCL-17
NEXTPNR_BUILD=../../../nextpnr/build

mkdir -p work
prjoxide interchange-export ${DEVICE} work/${DEVICE}.capnp
python3 -m fpga_interchange.nextpnr_emit --schema_dir ../../3rdparty/fpga-interchange-schema/interchange \
	--output_dir work --device work/${DEVICE}.capnp --bel_bucket_seeds nexus_bel_buckets.yaml
${NEXTPNR_BUILD}/bba/bbasm --l work/chipdb.bba work/${DEVICE}.bin
${NEXTPNR_BUILD}/nextpnr-fpga_interchange --chipdb work/${DEVICE}.bin --test
