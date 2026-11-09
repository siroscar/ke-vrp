# Kenya election-material delivery: HFVRP-TW experiment

Heterogeneous-fleet VRP with time windows (road + air), solved with **Hybrid Genetic Search**
(PyVRP) and compared against a **greedy nearest-neighbour** dispatcher baseline.

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
.
