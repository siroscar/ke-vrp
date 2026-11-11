"""CLI experiment runner.

  python -m kvrp.run --sizes 50 100 --seeds 3 --runtime 20 --fleets mixed road_only --out results/main
  python -m kvrp.run --csv data/county.csv --depot 0.35 37.58 --runtime 60 --out results/real
"""
from __future__ import annotations

import argparse
import pathlib

import pandas as pd

from .fleet import FLEETS
from .instance import generate_instance, load_csv
from .pipeline import run_both


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sizes", type=int, nargs="+", default=[50])
    ap.add_argument("--seeds", type=int, default=3)
    ap.add_argument("--runtime", type=float, default=20, help="HGS wall-clock seconds per run")
    ap.add_argument("--fleets", nargs="+", default=["mixed", "road_only"], choices=list(FLEETS))
    ap.add_argument("--deadline-h", type=float, default=12.0)
    ap.add_argument("--csv", help="real instance CSV (overrides --sizes)")
    ap.add_argument("--depot", type=float, nargs=2, metavar=("LAT", "LON"))
    ap.add_argument("--out", default="results/run")
    ap.add_argument("--plot", action="store_true", help="save a static PNG route map for each run")
    ap.add_argument("--map", action="store_true", help="save an interactive HTML map for each run")
    a = ap.parse_args()

    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    rows = []

    if a.csv:
        if not a.depot:
            ap.error("--depot LAT LON is required with --csv")
        jobs = [(load_csv(a.csv, *a.depot, deadline_h=a.deadline_h), 0)]
    else:
        jobs = [(generate_instance(n, seed=s, deadline_h=a.deadline_h), s)
                for n in a.sizes for s in range(a.seeds)]

    for inst, seed in jobs:
        for fname in a.fleets:
            fleet = FLEETS[fname]
            sub, mats, n_unserv, res = run_both(inst, fleet, a.runtime, seed)
            for method, (m, secs, routes) in res.items():
                rows.append(dict(
                    instance=inst.name, n=len(inst.stations), seed=seed, fleet=fname,
                    method=method, unservable=n_unserv, unserved_by_method=m.unserved,
                    feasible=m.feasible, cost=m.cost, total_km=round(m.total_km, 1),
                    vehicles=sum(m.vehicles_used.values()),
                    heli=m.vehicles_used.get("helicopter", 0),
                    makespan_h=round(m.makespan_h, 2),
                    mean_delivery_h=round(m.mean_delivery_h, 2),
                    runtime_s=round(secs, 2)))
                print(f"{inst.name:16s} {fname:9s} {method:9s} feas={m.feasible!s:5s} "
                      f"cost={m.cost:>10,} veh={sum(m.vehicles_used.values()):>2} "
                      f"unserv={m.unserved + n_unserv}")
            if a.map:
                from .imap import build_map
                build_map(sub, fleet, mats,
                          {k: v[2] for k, v in res.items()}, out / f"{inst.name}_{fname}.html",
                          metrics={k: v[0] for k, v in res.items()}, n_unservable=n_unserv)
            if a.plot:
                from .plot import plot_routes
                plot_routes(sub, fleet, res["hgs"][2], out / f"{inst.name}_{fname}_hgs.png")
                plot_routes(sub, fleet, res["greedy_nn"][2], out / f"{inst.name}_{fname}_nn.png")

    df = pd.DataFrame(rows)
    df.to_csv(out / "results.csv", index=False)

    piv = df.pivot_table(index=["n", "fleet"], columns="method",
                         values=["cost", "vehicles", "makespan_h", "unservable"], aggfunc="mean")
    piv[("cost", "hgs_saving_%")] = 100 * (1 - piv[("cost", "hgs")] / piv[("cost", "greedy_nn")])
    print("\n=== means over seeds ===")
    print("NB: costs are only comparable across fleets when `unservable` is equal;\n"
          "    road_only drops stations it cannot reach (see unservable), so it looks cheaper.")
    print(piv.round(1).to_string())
    print(f"\nfull results -> {out/'results.csv'}")


if __name__ == "__main__":
    main()