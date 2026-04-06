# Overview

At it's most basic level, the nexus (and most other FPGAs) is composed of basic elements (BELs), pins, wires and 
Programmable Interconnect Points (PIPs). The bitstream configures the BELs and which PIPs are active.

Loosely speaking, on the lattice components each BEL corresponds to a site. The internal tooling for lattice refers to 
wires as nodes and the terms are used interchangeably. 

The lattice parts overlay a tile grid over this structure. Largely speaking the tile grid informs on where the component
might be on the chip, but also where the configuration data can be found / specified for any given chip. 

## Sites (BELs)

Every site has a type, and the type dictates both it's pin capabilities and what programmable options and modes exist for
that given site. Sites correspond most closely to the primitives found in lattice documentation, but sometimes a site
isn't directly translated as a primitive, and instead has multiple modes which map the same site to multiple primitives
as defined in the manual.

Nearly every site name contains a prefix indicating the row and column it is most aligned to, and that tile is used to 
configure that site. A tile can have multiple sites in it, or the same site type can occur in multiple tile types where
it's configuration bits occur at different offsets. 

Many exceptions do exist where a site is named for one row-column pair but it's configuration lives in another tile, and
that tile has the appropriate tile type. For instance, LRAM's typically are like this. Part of what the fuzzers are configured
for is to represent the mapping between the site tile location and the config tile location. 

## Nodes (Wires) and PIPs

Nodes represent physical wires with gates connecting it to other nodes. Nodes can have pins tied directly onto them.

Lattice has a TCL library exposed in a tool -- lapie / lark depending on version -- which can be used to query the node 
graph. This tooling gives you which PIPs and pins are associated with the node, as well as what aliases are associated
with it. 

In terms of scale, there are about 1.7 million nodes on the LIFCL-40 part.

Nodes also have aliases. The typical reason for this is that nodes can span multiple tiles, and so each tile has a local
name for that node. Only the primary name associated with the node is directly queryable, so there is no robust way in 
general to determine every node that is associated with a given tile.

Generally -- although not universally -- a pip's config is located at the destination node's tile of the PIP. 

### Node Naming

Nodes have a semantically meaningful structure to their naming. They are all prefixed with `R<r>C<c>_` which gives a hint
to it's location; although nodes can span multiple tiles.

#### J.* 

These describe nodes local to the tile and often tie in to pins

#### [HV]0(D)[NEWS]0[C]0[S]

These describe horizontal or vertical wires that cross (D+1) tiles in N/E/W/S direction starting from where S is 0. There
can be multiple channels of these nodes per a given wire denoted with C. 

Special names and configuration is given when these nodes run into the edge of the chip. These nodes all have aliases 
that show what they branch across. 

The 'real' name for these nodes correspond to the middle position. The tile that typically configures them is the one in
the zero slot. 

For LIFCL-33U:

- R4C14:PLC configures R2C14_V06N0002: ['R0C14_A06N0003', 'R1C14_V06N0003', 'R2C14_V06N0002', 'R3C14_V06N0001', 'R4C14_V06N0000']
- R5C14:PLC configures 'R8C14_V06S0003': ['R10C14_V06S0005', 'R11C14_V06S0006', 'R5C14_V06S0000', 'R6C14_V06S0001', 'R7C14_V06S0002', 'R8C14_V06S0003', 'R9C14_V06S0004']
- R11C10:PLC configures R11C13_H06E0203: ['R11C10_H06E0200', 'R11C11_H06E0201', 'R11C12_H06E0202', 'R11C13_H06E0203', 'R11C14_H06E0204', 'R11C15_H06E0205', 'R11C16_H06E0206']
- R11C16:PLC configures R11C13_H06W0203: ['R11C10_H06W0206', 'R11C11_H06W0205', 'R11C12_H06W0204', 'R11C13_H06W0203', 'R11C14_H06W0202', 'R11C15_H06W0201', 'R11C16_H06W0200']
- CIB_R1C14:CIB_T configures 'R4C14_V06S0003': ['R1C14_V06S0000', 'R2C14_V06S0001', 'R3C14_V06S0002', 'R4C14_V06S0003', 'R5C14_V06S0004', 'R6C14_V06S0005', 'R7C14_V06S0006']

## Tile types

Tiles of a given tile type will always have the same set of:

- Sites
- Nodes
- PIPs

Often they will also dictate the relationship between neighboring tiles in a rigid way. For instance, LRAM instances
have an associated `CIB_LR` tiletype at an offset determined by it's tiletype. 

Tile types also are the fundamental building block to configuring the chip since it rigidly maps the bits in it's 
configuration bits to the sites and pips associated with it. 

Tile types are also standard across devices -- the way you configure a PLC tile is identical in LIFCL-17 as it is in LIFCL-40,
for instance. It should be noted though that lattice is inconsistent with this principal, and so some tile types are
flagged and changed when the tilegrid is imported from lattice's interchange format. 

## Global Routes

There is a global distribution network on the LIFCL devices for clocks and resets to limit skew to any given logic cell:

- Starts at CMUX 
- Branch out left or right -- LHPRX or RHPRX
- Distributed along HROW's to SPINEs - HPRX1000 -> VPSX1000
- SPINEs push to branch nodes VPSX1000 -> R..C44_HPBX..00
- PLCs local to the SPINE can be fed from here. An additional branch jump HPBX0 can reach the rest.

See global.json for a listing of those cells for each device.

### Example routing:

To get from R82C25_JCLKO_DCC_DCC0 -> R4C35_JCLK_SLICED on LIFCL-33

- R37C25_JCLKO_DCC_DCC0 feeds [R37C25_JJCLKUL_CMUX_CORE_CMUX0, R37C25_JJCLKUL_CMUX_CORE_CMUX1]
- These feed out to [R37C25_JHPRX{LANE}_CMUX_CORE_CMUX0, R37C25_JHPRX{LANE}_CMUX_CORE_CMUX1] respectively
- These feed out to [R37C25_LHPRX{LANE}, R37C25_RHPRX{LANE}]. LHPRX branches out to C0 to C25. RHPRX branches out from C25 to C50
- Following R37C25_LHPRX{LANE}, it drives R37C31_HPRX{LANE}00
- This drives R41C37_VPSX{LANE}00
- R41C37_VPSX{LANE}00 drives R{ROW}C44_HPBX{INST}00
- R4C32_HPBX{INST}00 provides local access to tiles R38 to R50. It also provides access to a branch R4C32_HPBX{INST}00 node.
- R4C32_HPBX{INST}00 provides local access to tiles R25 to R37, namely R4C35_JCLK1
- R4C35_JCLK1 drives R4C35_JCLK_SLICED

