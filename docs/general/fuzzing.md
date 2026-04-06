# Overview

The primary thing to solve for to be able to run placement and routing on a given device is the relationship between BELs
that nextpnr understands to sites on the device, as well as the routing pips available, and what bits need to be flipped
in the bitstream frames to achieve a given route / BEL configuration.

The main process is to create a minimal verilog file with the features that need to be isolated, generate a bitstream 
from that file, and compare it to a baseline bitstream without that feature. This generates a bitstream delta which is
represented as a list of (tile, frame, bit) tuples which changed between the two.

The main difficulty presented is that generating a bitstream takes a few seconds, and given the scale of number of things
to test, some care has to be taken to minimize the state space to attempt. To completely map a single device requires
thousands to tens of thousands of bitstream generations.

The results of all this fuzzing ends up in the database.

## BEL Fuzzing

BEL fuzzing tends to be straightforward, although it does rely on knowing how to configure the primitive in question, in
terms of what options it supports and how to specify those options. Most configuration options can be fuzzed in isolation
with the others which keeps down the number of bitstreams to generate.

### Enum Fuzzing

Many primitives have documented series of enumerated values. One bitstream is typically generated per enum value, and the
mapping is relatively simple. The main work required here is to identify which options are valid and when they are 
operative. 

### Word Fuzzing

Word fuzzing is conceptually the same as enum fuzzing, but is used against parameters that exist as integers. There is
an assumption here that a word of `N` bits long will require only `N` evaluations to map; ie that any bit in the value
maps to only one bit in the config block. Otherwise something like the initialization values of a LUT would be intractable.

## PIP Fuzzing

PIP fuzzing is the most difficult aspect to constrain to a limited number of trials. We can test these by placing a single
ARC (with a SLICE so it is not optimized away), and then looking at which tiles were impacted. This is usually done by
passing in a set of nodes to pull the PIPs from, and then creating a design with each of those pips placed in isolation.

While BEL fuzzing tends to operate against only one or two tiles at a time, a given node is hard to constrain to a given
tile. Some PIPs are also predicated on a related site being active. 

Some edges between nodes are always active. These are detected by placing the ARC and observing no change in relevant 
tiles. These are refered to as 'connections' in the database. For fuzzing purposes, it is important to pass the correct 
ignore list to the solver since if an irrelevant tile has a change in it, it will not mark it as a pure connection. 