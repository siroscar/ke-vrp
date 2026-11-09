from __future__ import annotations

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from .evaluate import Route
from .fleet import VehicleSpec
from .instance import Instance

COLORS = {"urban": "#1f77b4", "peri": "#2ca02c", "remote": "#d62728"}


def plot_routes(inst: Instance, fleet: list[VehicleSpec], routes: list[Route], path):
    fig, ax = plt.subplots(figsize=(8, 8))
    for s in inst.stations:
        ax.scatter(s.lon, s.lat, s=14, c=COLORS[s.area], marker="s" if not s.road_ok else "o", zorder=3)
    for k, r in enumerate(routes):
        v = fleet[r.spec]
        xs = [inst.depot_lon] + [inst.stations[i].lon for i in r.stops] + [inst.depot_lon]
        ys = [inst.depot_lat] + [inst.stations[i].lat for i in r.stops] + [inst.depot_lat]
        ax.plot(xs, ys, "--" if v.mode == "air" else "-", lw=1.6 if v.mode == "air" else 0.8,
                alpha=0.8, color=f"C{k % 10}", zorder=2)
    ax.scatter(inst.depot_lon, inst.depot_lat, marker="*", s=250, c="k", zorder=4)
    ax.set_title(f"{inst.name}: {len(routes)} routes (dashed = air, squares = no road access)")
    ax.set_xlabel("lon"); ax.set_ylabel("lat"); ax.set_aspect("equal")
    fig.tight_layout(); fig.savefig(path, dpi=110); plt.close(fig)
