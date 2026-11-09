# Kenya election-material delivery: HFVRP-TW experiment

Heterogeneous-fleet VRP with time windows (road + air), solved with **Hybrid Genetic Search**
(PyVRP) and compared against a **greedy nearest-neighbour** dispatcher baseline.

## Run (Docker)
```bash
make build        # build image
make test         # 3 tests, incl. evaluator-vs-solver cost agreement
make smoke        # ~1 min sanity run
make experiment   # n=50/100/200, 5 seeds, 30 s HGS per run
```
VS Code: "Dev Containers: Reopen in Container" (uses `.devcontainer/devcontainer.json`).

Without Docker: `pip install -r requirements.txt && PYTHONPATH=src python -m kvrp.run --plot`

## Layout
| file | role |
|---|---|
| `instance.py` | synthetic county generator (urban / peri-urban / remote) + `load_csv()` for real data |
| `fleet.py` | vehicle types: capacity, speed, fixed cost, cost/km, shift, range (**placeholder costs**) |
| `travel.py` | per-vehicle-type distance/time matrices (road = circuity + terrain; air = straight line) |
| `baseline.py` | greedy NN, cheapest-per-capacity vehicles first, aircraft last |
| `hgs.py` | PyVRP model: one VehicleType + travel profile per fleet spec |
| `evaluate.py` | solver-independent feasibility + cost + KPIs (scores BOTH methods) |
| `run.py` | experiment CLI -> `results.csv` + summary table (+ route maps with `--plot`) |

## Real data CSV (`--csv`)
Columns: `id, lat, lon, demand` (+ optional `area, road_ok, tw_early_h, tw_late_h, service_min`).
`python -m kvrp.run --csv data/county.csv --depot LAT LON --runtime 60`

## Modelling choices to revisit
* Closed routes (vehicles return to the depot); delivery deadline = station `tw_late`.
* Stations with no road access are only reachable by the air vehicles; stations no vehicle can
  reach at all are reported as `unservable` rather than silently dropped.
* Single depot. Multi-depot (constituency offices) is a small extension in `hgs.py`.
* Demand is in abstract "box equivalents"; all costs/speeds are illustrative.
* `Model.add_edge` is a Python loop: fine to ~500 stations; beyond that build `ProblemData` directly.
