"""Problem instances: polling stations, a depot, and a delivery deadline.

Two sources:
  * generate_instance(): synthetic, seeded, urban/peri-urban/remote mix.
  * load_csv():            real data (IEBC station list + coordinates + your own demand model).

All times are seconds from dispatch (t=0 at the depot, e.g. 06:00).
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd

AREA_TYPES = ("urban", "peri", "remote")


@dataclass(frozen=True)
class Station:
    id: str
    lat: float
    lon: float
    demand: int          # ballot-box / kit equivalents
    area: str            # urban | peri | remote
    road_ok: bool        # False => only reachable by air (washed-out roads, islands, etc.)
    tw_early_s: int
    tw_late_s: int       # delivery deadline
    service_s: int       # unloading + handover time


@dataclass
class Instance:
    name: str
    depot_lat: float
    depot_lon: float
    stations: list[Station]
    deadline_s: int

    def subset(self, idx: list[int]) -> "Instance":
        return Instance(self.name, self.depot_lat, self.depot_lon,
                        [self.stations[i] for i in idx], self.deadline_s)


def haversine_matrix(lats: np.ndarray, lons: np.ndarray) -> np.ndarray:
    """Great-circle distance matrix in km."""
    phi = np.radians(lats)
    lam = np.radians(lons)
    dphi = phi[:, None] - phi[None, :]
    dlam = lam[:, None] - lam[None, :]
    a = np.sin(dphi / 2) ** 2 + np.cos(phi)[:, None] * np.cos(phi)[None, :] * np.sin(dlam / 2) ** 2
    return 2 * 6371.0088 * np.arcsin(np.sqrt(np.clip(a, 0, 1)))


def _offset(lat0: float, lon0: float, dx_km: float, dy_km: float) -> tuple[float, float]:
    return (lat0 + dy_km / 111.32,
            lon0 + dx_km / (111.32 * math.cos(math.radians(lat0))))


def generate_instance(
    n: int,
    seed: int = 0,
    depot: tuple[float, float] = (0.3546, 37.5822),  # illustrative: a county HQ in northern Kenya
    deadline_h: float = 12.0,
    urban_frac: float = 0.35,
    peri_frac: float = 0.35,
    no_road_frac_of_remote: float = 0.25,
    windowed_frac: float = 0.25,
) -> Instance:
    """Synthetic county: dense urban core, peri-urban ring, sparse remote periphery.

    NOTE: purely synthetic. Geography is only loosely 'Kenya-like'. Replace with
    load_csv() once you have real station coordinates.
    """
    rng = np.random.default_rng(seed)
    deadline_s = int(deadline_h * 3600)
    n_urban = int(round(n * urban_frac))
    n_peri = int(round(n * peri_frac))
    n_remote = n - n_urban - n_peri

    stations: list[Station] = []

    def add(kind: str, k: int, sampler, demand_rng, service_min: int):
        for _ in range(k):
            dx, dy = sampler()
            lat, lon = _offset(depot[0], depot[1], dx, dy)
            road_ok = True
            if kind == "remote" and rng.random() < no_road_frac_of_remote:
                road_ok = False
            early, late = 0, deadline_s
            if kind != "remote" and rng.random() < windowed_frac:
                # e.g. school head / security escort only available in a window
                early = int(rng.integers(1, 4)) * 3600
                late = min(deadline_s, early + int(rng.integers(4, 7)) * 3600)
            stations.append(Station(
                id=f"PS{len(stations):05d}", lat=lat, lon=lon,
                demand=int(rng.integers(*demand_rng)), area=kind, road_ok=road_ok,
                tw_early_s=early, tw_late_s=late, service_s=service_min * 60))

    def gauss_urban():
        return rng.normal(0, 4, 2)

    def ring(lo, hi):
        def f():
            r = rng.uniform(lo, hi)
            th = rng.uniform(0, 2 * math.pi)
            return r * math.cos(th), r * math.sin(th)
        return f

    add("urban", n_urban, gauss_urban, (4, 11), 15)
    add("peri", n_peri, ring(5, 40), (2, 9), 20)
    add("remote", n_remote, ring(40, 130), (1, 6), 30)
    return Instance(f"synth_n{n}_s{seed}", depot[0], depot[1], stations, deadline_s)


def load_csv(path: str, depot_lat: float, depot_lon: float, deadline_h: float = 12.0,
             name: str | None = None) -> Instance:
    """Load real data. Required columns: id, lat, lon, demand.
    Optional: area (urban|peri|remote), road_ok (0/1), tw_early_h, tw_late_h, service_min.
    """
    df = pd.read_csv(path)
    deadline_s = int(deadline_h * 3600)
    stations = []
    for r in df.itertuples(index=False):
        g = r._asdict()
        stations.append(Station(
            id=str(g["id"]), lat=float(g["lat"]), lon=float(g["lon"]),
            demand=int(g["demand"]), area=str(g.get("area", "peri")),
            road_ok=bool(int(g.get("road_ok", 1))),
            tw_early_s=int(float(g.get("tw_early_h", 0)) * 3600),
            tw_late_s=int(float(g.get("tw_late_h", deadline_h)) * 3600),
            service_s=int(float(g.get("service_min", 20)) * 60)))
    return Instance(name or path, depot_lat, depot_lon, stations, deadline_s)
