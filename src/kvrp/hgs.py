"""Hybrid Genetic Search (via PyVRP) for the HFVRP-TW.

PyVRP's solver is an HGS implementation (Vidal et al.) with adaptive penalties for
capacity / time-warp / distance violations. Each VehicleSpec becomes one VehicleType with
its own travel profile, which is how the road/air split is expressed.
"""
from __future__ import annotations

from pyvrp import Model
from pyvrp.stop import MaxRuntime

from .evaluate import Route
from .fleet import VehicleSpec
from .instance import Instance


def solve_hgs(inst: Instance, fleet: list[VehicleSpec], mats, runtime_s: float, seed: int = 0):
    m = Model()
    depot = m.add_depot(m.add_location(x=inst.depot_lon, y=inst.depot_lat))
    profiles = [m.add_profile(name=v.name) for v in fleet]

    for v, prof in zip(fleet, profiles):
        m.add_vehicle_type(
            num_available=v.count,
            capacity=[v.capacity],
            start_depot=depot, end_depot=depot,
            fixed_cost=v.fixed_cost,
            tw_early=0, tw_late=int(v.shift_h * 3600),
            unit_distance_cost=v.cost_per_hm,
            unit_duration_cost=0,
            max_distance=int(v.max_km * 10) if v.max_km else 2**62,
            profile=prof, name=v.name,
        )

    for s in inst.stations:
        loc = m.add_location(x=s.lon, y=s.lat)
        m.add_client(loc, delivery=[s.demand], service_duration=s.service_s,
                     tw_early=s.tw_early_s, tw_late=s.tw_late_s, name=s.id)

    locs = m.locations
    for prof, (dist, dur) in zip(profiles, mats):
        for i, a in enumerate(locs):
            for j, b in enumerate(locs):
                m.add_edge(a, b, distance=int(dist[i, j]), duration=int(dur[i, j]), profile=prof)

    res = m.solve(stop=MaxRuntime(runtime_s), seed=seed, display=False)
    routes = [Route(r.vehicle_type(), [a.idx for a in r.schedule() if a.is_client()])
              for r in res.best.routes()]
    return routes, res
