# Overview

The tiletype of a tile dictates which BEL's are available on a given tile and which options they might have exposed. This is mapped out fully in prjoxide/libprjoxide/prjoxide/src/bels.rs, namely in `get_tile_bels`.

A given bel might span over multiple logical tiles. It's anchor tile is the one with the appropriate tiletype but for routing information on where the related tile is there is rel_x and rel_y; which encode the relative tile offset for the related tile. This data can be varied based on the family, device and actual tile in question. 

For bels with these offsets, the offset information is used in fuzzing the routing to map the interconnect. The offset themselves can be derived from the output of the dev_get_nodes command and report for nearby CIB tiles. For instance, related tiles to LRAM will have LRAM_CORE wires in their tile. 

Bel information is encoded in the bba file which is produced by prjoxide and ingested in the build process of nextpnr. 

# References

- [Terminology](https://fpga-interchange-schema.readthedocs.io/device_resources.html)

