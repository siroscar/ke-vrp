"""Greedy nearest-neighbour baseline for the heterogeneous fleet with time windows.

Policy (deliberately simple, i.e. what a competent dispatcher might do by hand):
  1. Order vehicles by fixed-cost per unit of capacity (cheap bulk carriers first,
     aircraft last).
  2. For each vehicle, repeatedly drive to the NEAREST unserved station that still fits
     (capacity, time window, shift end incl. return, range). Stop when nothing fits.
  3. Next vehicle. Stations nobody can take stay unserved.
"""
from __future__ import annotations

from .evaluate import Route
from .fleet import VehicleSpec
from .instance import Instance
from .travel import BIG


def greedy_nn(inst: Instance, fleet: list[VehicleSpec], mats) -> list[Route]:
    unserved = set(range(len(inst.stations)))
    order = sorted(range(len(fleet)), key=lambda k: fleet[k].fixed_cost / fleet[k].capacity)
    routes: list[Route] = []

    for k in order:
        v = fleet[k]
        dist, dur = mats[k]
        for _ in range(v.count):
            if not unserved:
                break
            t, prev, load, d = 0, 0, 0, 0
            stops: list[int] = []
            while True:
                best, best_d = None, None
                for s in unserved:
                    st = inst.stations[s]
                    node = s + 1
                    if dist[prev, node] >= BIG or load + st.demand > v.capacity:
                        continue
                    arrive = max(t + int(dur[prev, node]), st.tw_early_s)
                    if arrive > st.tw_late_s:
                        continue
                    if arrive + st.service_s + int(dur[node, 0]) > v.shift_h * 3600:
                        continue
                    if v.max_km is not None and d + dist[prev, node] + dist[node, 0] > v.max_km * 10:
                        continue
                    if best_d is None or dist[prev, node] < best_d:
                        best, best_d = s, int(dist[prev, node])
                if best is None:
                    break
                node = best + 1
                st = inst.stations[best]
                t = max(t + int(dur[prev, node]), st.tw_early_s) + st.service_s
                d += int(dist[prev, node])
                load += st.demand
                prev = node
                stops.append(best)
                unserved.discard(best)
            if stops:
                routes.append(Route(k, stops))
    return routes
