"""Travel matrices per vehicle type.

Units: distance in hectometres (0.1 km) so costs stay integer; time in seconds.
Road vehicles: haversine * circuity, slowed by terrain; stations with road_ok=False are
effectively unreachable (BIG arc). Air: straight line, fixed speed.
"""
from __future__ import annotations

import numpy as np

from .fleet import VehicleSpec
from .instance import Instance, haversine_matrix

BIG = 10_000_000

CIRCUITY = {"urban": 1.25, "peri": 1.30, "remote": 1.60}
TERRAIN_SPEED = {"urban": 0.60, "peri": 1.00, "remote": 0.60}  # congestion / dirt roads


def _node_attrs(inst: Instance):
    areas = ["depot"] + [s.area for s in inst.stations]
    road_ok = np.array([True] + [s.road_ok for s in inst.stations])
    circ = np.array([1.0] + [CIRCUITY[s.area] for s in inst.stations])
    speed = np.array([1.0] + [TERRAIN_SPEED[s.area] for s in inst.stations])
    return areas, road_ok, circ, speed


def build_matrices(inst: Instance, fleet: list[VehicleSpec]):
    """Returns list of (dist_hm[int64], dur_s[int64]) aligned with `fleet`."""
    lats = np.array([inst.depot_lat] + [s.lat for s in inst.stations])
    lons = np.array([inst.depot_lon] + [s.lon for s in inst.stations])
    gc = haversine_matrix(lats, lons)
    _, road_ok, circ, spd = _node_attrs(inst)
    out = []
    for v in fleet:
        if v.mode == "air":
            km = gc
            kmh = np.full_like(gc, v.speed_kmh)
        else:
            km = gc * np.maximum(circ[:, None], circ[None, :])
            kmh = v.speed_kmh * np.minimum(spd[:, None], spd[None, :])
        dist = np.rint(km * 10).astype(np.int64)
        dur = np.rint(km / kmh * 3600).astype(np.int64)
        if v.mode == "road":
            bad = ~(road_ok[:, None] & road_ok[None, :])
            np.fill_diagonal(bad, False)
            dist[bad] = BIG
            dur[bad] = BIG
        np.fill_diagonal(dist, 0)
        np.fill_diagonal(dur, 0)
        out.append((dist, dur))
    return out


def reachable_stations(inst: Instance, fleet: list[VehicleSpec], mats) -> list[int]:
    """Stations that at least one vehicle type could serve on a dedicated round trip
    (capacity, deadline, shift, range). Anything else is reported as 'unservable'."""
    keep = []
    for i, s in enumerate(inst.stations):
        j = i + 1
        for v, (dist, dur) in zip(fleet, mats):
            if s.demand > v.capacity:
                continue
            arrive = max(int(dur[0, j]), s.tw_early_s)
            if int(dur[0, j]) > s.tw_late_s:
                continue
            if arrive + s.service_s + int(dur[j, 0]) > v.shift_h * 3600:
                continue
            if v.max_km is not None and (dist[0, j] + dist[j, 0]) > v.max_km * 10:
                continue
            keep.append(i)
            break
    return keep


def slice_mats(mats, kept: list[int]):
    idx = np.array([0] + [i + 1 for i in kept])
    return [(d[np.ix_(idx, idx)], t[np.ix_(idx, idx)]) for d, t in mats]
