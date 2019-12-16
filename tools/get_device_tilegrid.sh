#!/usr/bin/bash

set -ex

GEN_RBF=1 ../radiant.sh $1 ../minitests/simple/wire.v

# Strip out bitstream data to prevent bstool crashing
# we only want tile offsets anyway
sed -i 's/^[01]\+$//g' ../minitests/simple/wire.rbt
../radiant_cmd.sh bstool -t  ../minitests/simple/wire.rbt > ../minitests/simple/wire.dump 2>/dev/null
