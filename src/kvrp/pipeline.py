"""One call that runs the full chain for a (instance, fleet) pair."""
from __future__ import annotations

import time

from .baseline import greedy_nn
from .evaluate import evaluate
from .fleet import VehicleSpec
from .hgs import solve_hgs
from .instance import Instance
from .travel import build_matrices, reachable_stations, slice_mats


def prepare(inst: Instance, fleet: list[VehicleSpec]):
    """Drop stations no vehicle in this fleet can serve (reported, not silently ignored)."""
    mats_full = build_matrices(inst, fleet)
    kept = reachable_stations(inst, fleet, mats_full)
    return inst.subset(kept), slice_mats(mats_full, kept), len(inst.stations) - len(kept)


def run_both(inst: Instance, fleet: list[VehicleSpec], runtime_s: float, seed: int = 0):
    sub, mats, n_unservable = prepare(inst, fleet)
    out = {}

    t0 = time.perf_counter()
    r_nn = greedy_nn(sub, fleet, mats)
    out["greedy_nn"] = (evaluate(sub, fleet, mats, r_nn), time.perf_counter() - t0, r_nn)

    t0 = time.perf_counter()
    r_hgs, _ = solve_hgs(sub, fleet, mats, runtime_s, seed)
    out["hgs"] = (evaluate(sub, fleet, mats, r_hgs), time.perf_counter() - t0, r_hgs)
    return sub, mats, n_unservable, out
