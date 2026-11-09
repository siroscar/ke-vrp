from kvrp.fleet import FLEETS
from kvrp.instance import generate_instance
from kvrp.pipeline import prepare, run_both
from kvrp.hgs import solve_hgs
from kvrp.evaluate import evaluate


def test_hgs_feasible_and_not_worse_than_greedy():
    inst = generate_instance(30, seed=1)
    _, _, _, res = run_both(inst, FLEETS["mixed"], runtime_s=3, seed=0)
    nn, hgs = res["greedy_nn"][0], res["hgs"][0]
    assert hgs.feasible, hgs.violations
    assert hgs.unserved == 0
    assert hgs.cost <= nn.cost


def test_evaluator_matches_pyvrp_cost():
    """Independent evaluator must agree with the solver's own objective."""
    inst = generate_instance(25, seed=2)
    fleet = FLEETS["mixed"]
    sub, mats, _ = prepare(inst, fleet)
    routes, res = solve_hgs(sub, fleet, mats, runtime_s=2, seed=0)
    m = evaluate(sub, fleet, mats, routes)
    assert m.feasible
    assert m.cost == res.cost()


def test_road_only_cannot_serve_roadless_stations():
    inst = generate_instance(60, seed=3, no_road_frac_of_remote=0.5)
    _, _, n_unserv_road, _ = run_both(inst, FLEETS["road_only"], runtime_s=1, seed=0)
    _, _, n_unserv_mixed, _ = run_both(inst, FLEETS["mixed"], runtime_s=1, seed=0)
    assert n_unserv_road > n_unserv_mixed
