import hashlib
import json
import logging
import os
import tempfile
import threading
import asyncio
from asyncio import CancelledError

import fuzzconfig
import tiles
from pathlib import Path
from os import path
import cachecontrol

workdir = tempfile.mkdtemp()

def create_design_file(config, elements, prefix = "", executor = None):
    if executor is not None:
        future = executor.submit(create_wires_file, config, elements, prefix)
        future.name = f"Build {config.device}"
        future.executor = executor
        return future

    all_outputs = [o for _, os, _ in elements for o in os]
    all_inputs = [i for ins, _, _ in elements for i in ins]

    blurb_text = "\n".join([b for _, _, b in elements])

    subst = config.subst_defaults()
    arch = config.device.split("-")[0]
    device = config.device
    package = subst["package"]
    speed_grade = subst["speed_grade"]

    outputs = ", ".join([f"output wire q_{o}" for o in all_outputs])
    input_ties = "\n".join([f"VHI vhi_i_{i}(.Z(q_{i}));" for i in all_inputs])

    source = f"""\
    (* \\db:architecture ="{arch}", \\db:device ="{device}", \\db:package ="{package}", \\db:speed ="{speed_grade}_High-Performance_1.0V", \\db:timestamp = 0, \\db:view ="physical" *)
    module top ({outputs});
    {input_ties}
    {blurb_text}
        	(* \\xref:LOG ="q_c@0@0" *)
    	VHI vhi_i();        
    endmodule        
            """
    h = abs(hash(source))
    vfile = path.join(workdir, f"{config.device}/{prefix}{config.job}-{h}.v")
    Path(vfile).parent.mkdir(parents=True, exist_ok=True)

    with open(vfile, 'w') as f:
        f.write(source)

    return config.build_design(vfile, prefix=prefix)

def create_wires_file(config, wires, prefix = "", executor = None):
    if executor is not None:
        future = executor.submit(create_wires_file, config, wires, prefix)
        future.name = f"Build {config.device}"
        future.executor = executor
        return future

    wires = sorted(wires)

    wires_txt = "\n".join([f"""
(*  keep = "true", dont_touch = "true", keep, dont_touch,\\xref:LOG ="q_c@0@0", \\dm:arcs ="{to}.{frm}" *)
wire q_{idx};
VHI vhi_i_{idx}(.Z(q_{idx}));
        """ for idx, (frm, to) in enumerate(sorted(wires))])

    outputs = ", ".join([f"output wire q_{idx}" for idx in range(len(wires))])
    subst = config.subst_defaults()
    arch = config.device.split("-")[0]
    device = config.device
    package = subst["package"]
    speed_grade = subst["speed_grade"]

    source = f"""\
(* \\db:architecture ="{arch}", \\db:device ="{device}", \\db:package ="{package}", \\db:speed ="{speed_grade}_High-Performance_1.0V", \\db:timestamp = 0, \\db:view ="physical" *)
module top ({outputs});
{wires_txt}
    	(* \\xref:LOG ="q_c@0@0" *)
	VHI vhi_i();        
endmodule        
        """

    h = abs(hash(source))
    vfile = path.join(workdir, f"{config.device}/{prefix}{config.job}-{h}.v")
    Path(vfile).parent.mkdir(parents=True, exist_ok=True)

    with open(vfile, 'w') as f:
        f.write(source)

    return config.build_design(vfile, prefix=prefix)

def get_wires_delta(device, wires, prefix = "", executor = None, with_bitstream_info=False, job_name = None):
    @cachecontrol.cache_fn()
    def _get_wires_delta(device, wires, prefix = "", with_bitstream_info=False):
        config = fuzzconfig.FuzzConfig(job=f"wires-delta", device=device)
        bitstream = create_wires_file(config, wires, prefix)
        if with_bitstream_info:
            return *fuzzconfig.find_baseline_differences(device, bitstream), bitstream
        return fuzzconfig.find_baseline_differences(device, bitstream)

    if executor is not None:
        f = executor.submit(_get_wires_delta, device, wires, prefix, with_bitstream_info=with_bitstream_info)
        if job_name is not None:
            f.name = job_name
        return f

    return _get_wires_delta(device, wires, prefix, with_bitstream_info)

def set_default(obj):
    if isinstance(obj, set):
        return sorted(obj)
    raise TypeError

async def DesignsForPips(device_tiles, anon_pips, shuffled_rcs_for_tiles_of_tiletype, modified_tiles_rcs_anon):

    device = device_tiles.device
    anon_pips = list(anon_pips)
    anon_pips_sig = hashlib.sha256(json.dumps((sorted(anon_pips), sorted(shuffled_rcs_for_tiles_of_tiletype)),
                                              default=set_default).encode()).hexdigest()

    last_anon_pips_remaining = len(anon_pips) + 1

    idx = 0
    while len(anon_pips):
        idx = idx + 1
        if last_anon_pips_remaining <= len(anon_pips):
            logging.error(f"Could not place {len(anon_pips)} {anon_pips}")

        logging.debug(f"Processing anon pips {len(anon_pips)}...")
        assert last_anon_pips_remaining > len(anon_pips)
        last_anon_pips_remaining = len(anon_pips)
        design_set = {}

        # Just place all the extra tiles. We don't have pips for these tiles but this marks it as used.
        for (tile, (r, c)) in shuffled_rcs_for_tiles_of_tiletype:
            if len(anon_pips) == 0:
                break

            anon_pip = anon_pips[-1]

            other_modified_tiles = {tiles.get_rc_from_name(device, t) for anon_tile in modified_tiles_rcs_anon
                                      for t in device_tiles.get_related_tiles(anon_tile, (r, c))}


            pip = [tiles.resolve_actual_node(device, n, (r, c)) for n in anon_pip]
            pip_coords = {rrcc for n in pip for rrcc in tiles.resolve_node_rcs(device, n)}
            pip_owner_tiles = {tiles.get_rc_from_name(device, tile)
                               for w in pip
                               for tile in tiles.get_tile_list_for_node(device, w)}

            all_touched_coords = pip_coords | other_modified_tiles | {(r, c)} | pip_owner_tiles
            all_touched_tiles = {tile for rc in all_touched_coords for tile in tiles.get_tiles_by_rc(device, rc)}
            if len(all_touched_tiles & design_set.keys()) > 0:
                continue

            anon_pips.pop()

            for t in all_touched_tiles: design_set[t] = None
            design_set[tile] = (pip, all_touched_coords)

        if len(design_set):
            sig = hashlib.sha256(json.dumps(sorted(design_set.items()), default=set_default).encode()).hexdigest()
            os.makedirs(f"/tmp/prjoxide/{device}/{anon_pips_sig}/{idx}", exist_ok=True)
            fn = f"/tmp/prjoxide/{device}/{anon_pips_sig}/{idx}/{sig}"
            if not path.exists(fn):
                with open(fn, "w") as f:
                    logging.warning(f"New signature {fn}")
                    json.dump(sorted(design_set.items()), f, default=set_default, indent=4)

            yield design_set

class BitConflictException(Exception):
    def __init__(self, device, nfrom_wire, nto_wire, tile, internal_exception):
        self.device = device
        self.from_wire = nfrom_wire
        self.to_wire = nto_wire
        self.tile = tile
        self.internal_exception = internal_exception

    async def solve_standalone(self):
        device = self.device
        gt_delta, _ = get_wires_delta(device, [(self.from_wire, self.to_wire)])
        logging.error(f"Encountered {self.internal_exception} adding pip {self.tile} {self.from_wire} -> {self.to_wire}. Isolated test delta: {gt_delta}. Args: {self.to_wire}")


# Exception for when a bitstream returns unexpected tile configs in DesignFileBuilder
class UnexpectedDeltaException(Exception):
    def __init__(self, device, unexpected_deltas, designs, bitstream_info, name = ""):
        super().__init__(f"Got unexpected deltas from {bitstream_info.vfiles}: {unexpected_deltas}")
        self.device = device
        self.designs = designs
        self.unexpected_deltas = unexpected_deltas
        self.name = name

    async def find_bad_design(self, executor = None):
        all_deltas = await asyncio.gather(*[get_wires_delta(self.device, [v for k, v in d.items() if v is not None],
                                                            prefix=f"unexpected_delta_{self.name}_{idx}",
                                                            executor=executor, with_bitstream_info=True) for
                                            idx, d in enumerate(self.designs)])
        for design, (deltas, *_) in zip(self.designs, all_deltas):
            delta_match = self.unexpected_deltas & set(deltas.keys())
            if len(delta_match) > 0:
                logging.error(f"Due to design: unexpected {delta_match} from {design}")
                return design
        return None

# Helper class that allows stacking designs to test so multiple things can be tested in one bitstream.
# Relies on each design submitted to fully annotate which tiles could potentially be modified
class DesignFileBuilder:
    def __init__(self, device, executor):
        self.device = device
        self.active_designs_lock = threading.Lock()
        self.active_designs_event = asyncio.Event()
        self.active_designs = []

        self._executor = executor
        self.runs = 0
        self.hasher = hashlib.sha1()

        self.wait_count = 0

        self.running = False
        self._emitted_sig_warning = False

    # Indicate that at some point in the future n new designs will be added. Nothing is built until all reserved slots
    # have been filled with designs
    def reserve(self, n = 1):
        with self.active_designs_lock:
            self.wait_count = self.wait_count + n

    def unreserve(self, n = 1):
        with self.active_designs_lock:
            self.wait_count = self.wait_count - n

    async def _run_design(self, designset, future, designset_list):
        wires = [v for k, v in designset.items() if v is not None]
        self.runs = self.runs + 1
        result = (deltas, ipdeltas, bitstream_info) = await get_wires_delta(self.device, wires,
                                                                            prefix=f"design-file-builder_{self.runs}_{len(wires)}_{len(designset)}",
                                                                            executor=self._executor, with_bitstream_info=True)
        unexpected_deltas = set(deltas.keys()) - set(designset.keys())
        if (len(unexpected_deltas) > 0):
            raise UnexpectedDeltaException(self.device, unexpected_deltas, designset_list, bitstream_info, name=f"{self.runs}_{len(wires)}_{len(designset)}")

        future.set_result(result)
        return result

    async def build_task(self):
        try:
            while self.wait_count == 0:
                await asyncio.sleep(1)
            self.running = True

            while self.wait_count > 0:
                await asyncio.sleep(1)

            with self.active_designs_lock:
                self.running = False
                logging.info(f"No more reservations, finishing design run with {len(self.active_designs)} designs for {sum([len([1 if v is not None else 0 for v in d[0].values()]) for d in self.active_designs])} pips")

                await asyncio.gather(
                    *[asyncio.create_task(self._run_design(*design_tuple), name=f"design-file-builder/build-{idx}")
                    for idx, design_tuple in enumerate(self.active_designs)]
                )

        except CancelledError:
            logging.info("Joining design file builder")

    async def _get_viable_design(self, designset):
        design_tuple = None

        prior = self.hasher.hexdigest()
        self.hasher.update(json.dumps(sorted(designset.items())).encode())

        fn = f"/tmp/prjoxide/viable-design-entry/{prior}/{self.hasher.hexdigest()}"
        os.makedirs(os.path.dirname(fn), exist_ok=True)

        if not path.exists(fn):
            with open(fn, "w") as f:
                if not self._emitted_sig_warning:
                    logging.warning(f"New signature {fn} at {len(self.active_designs)} designs")

                self._emitted_sig_warning = True
                json.dump(sorted(designset), f, default=set_default, indent=4)

        with self.active_designs_lock:
            for (d, full_design_future, design_list) in self.active_designs:
                if len(d.keys() & designset.keys()) == 0:
                    d.update(designset)
                    design_list.append(designset)

                    design_tuple = (d, full_design_future, design_list)
                    break
            else:
                design_tuple = (dict(designset), asyncio.get_running_loop().create_future(), [designset])
                self.active_designs.append(design_tuple)

            self.wait_count = self.wait_count - 1

        self.active_designs_event.set()

        return await design_tuple[1]

    # Submit the given design to the builder. Only returns when that design has been built.
    async def build_design(self, designset):
        assert self.running
        (full_delta, ipdeltas, bitstream_info) = await self._get_viable_design(designset)
        return {k:v for k,v in full_delta.items() if k in designset}, bitstream_info
