"""Solver-independent route evaluator. Both the baseline and HGS are scored with this, so
the comparison cannot be skewed by either solver's internal bookkeeping."""
from __future__ import annotations

from dataclasses import dataclass, field

from .fleet import VehicleSpec
from .instance import Instance


@dataclass
class Route:
    spec: int            # index into fleet
    stops: list[int]     # station indices (0-based, into instance.stations)


@dataclass
class Metrics:
    feasible: bool
    cost: int
    served: int
    unserved: int
    vehicles_used: dict[str, int]
    total_km: float
    makespan_h: float            # time of the last delivery completion
    mean_delivery_h: float
    violations: list[str] = field(default_factory=list)


def evaluate(inst: Instance, fleet: list[VehicleSpec], mats, routes: list[Route]) -> Metrics:
    n = len(inst.stations)
    seen: dict[int, int] = {}
    viol: list[str] = []
    used: dict[str, int] = {v.name: 0 for v in fleet}
    cost = 0
    total_hm = 0
    arrivals: list[int] = []
    last_done = 0

    per_spec_routes = {k: 0 for k in range(len(fleet))}

    for r in routes:
        if not r.stops:
            continue
        v = fleet[r.spec]
        dist, dur = mats[r.spec]
        per_spec_routes[r.spec] += 1
        used[v.name] += 1
        t, prev, load, d = 0, 0, 0, 0
        for s in r.stops:
            seen[s] = seen.get(s, 0) + 1
            st = inst.stations[s]
            node = s + 1
            t += int(dur[prev, node])
            d += int(dist[prev, node])
            if t < st.tw_early_s:
                t = st.tw_early_s
            if t > st.tw_late_s:
                viol.append(f"{st.id}: late by {(t - st.tw_late_s) / 3600:.1f}h ({v.name})")
            arrivals.append(t)
            t += st.service_s
            last_done = max(last_done, t)
            load += st.demand
            prev = node
        t += int(dur[prev, 0])
        d += int(dist[prev, 0])
        if load > v.capacity:
            viol.append(f"{v.name}: load {load} > cap {v.capacity}")
        if t > v.shift_h * 3600:
            viol.append(f"{v.name}: back at depot after shift")
        if v.max_km is not None and d > v.max_km * 10:
            viol.append(f"{v.name}: range exceeded")
        cost += v.fixed_cost + d * v.cost_per_hm
        total_hm += d

    for k, v in enumerate(fleet):
        if per_spec_routes[k] > v.count:
            viol.append(f"{v.name}: {per_spec_routes[k]} routes > fleet size {v.count}")
    for s, c in seen.items():
        if c > 1:
            viol.append(f"{inst.stations[s].id}: visited {c} times")

    served = len(seen)
    return Metrics(
        feasible=not viol,
        cost=cost, served=served, unserved=n - served,
        vehicles_used=used, total_km=total_hm / 10,
        makespan_h=last_done / 3600,
        mean_delivery_h=(sum(arrivals) / len(arrivals) / 3600) if arrivals else 0.0,
        violations=viol,
    )
