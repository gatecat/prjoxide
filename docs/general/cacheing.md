# Cacheing

The fuzzers all require a lot of runtime in building bitfiles and pulling data from radiant tools. 

## Bitstream cacheing

The main cacheing mechanism is the bitstreamcache -- tools/bitstreamcache.py. This stores checksums for input files and
the bitstream in `.bitstreamcache`. 

The bitstreams are stored compressed and libprjoxide can read them compressed. Instead of copying the files around, the
cache fetch generates symbolic links. 

This folder should be cleared very rarely.

## Stored deltas

Each solve generates serialized delta files in `.deltas` of the given fuzzer. This is useful to see what changed for each
solver run, but is also used as a marker -- if that file exists, the solver assumes it has been applied already and skips
generating / fetching bitstreams and calling into the fuzzer solvers. 

Delete these folders when making heavy changes to fuzz.rs or other portions of the rust library.

## Lapie cache database

Lapie / Lark is a radiant tool used to query the internal chip lattice database. Each run of this program has around
10 seconds of overhead and it only returns around 60 results per second after that.

To speed these accesses up, a sqlite database is generated at `.cache/<radiant version>/<device>-nodes.sqlite` to cache
the results of these queries. Specifically, it caches node data and site data per device as well as the jumpwires list.

Queries, once cached, return nearly instantaneously in comparison, but these files do end up being around 100M in size. 

## Cachier

Other methods are annotated with cachier -- a decoration that caches calls into a function by its arguments. These
entries are stored in `.cache/<radiant version>/cache.db`. 