"""Regression tests for physical accounting and scenario interpretation."""
from pathlib import Path
import sys
import json
import networkx as nx
import numpy as np
import pandas as pd
import pypsa
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from pypsa_sudan.model import build_network, hydro_constraints, check_solution


@pytest.fixture(scope="module")
def solved():
    n = build_network(hours=24)
    status, condition = n.optimize(solver_name="highs", extra_functionality=hydro_constraints, solver_options={"threads": 1, "random_seed": 0})
    assert (status, condition) == ("ok", "optimal")
    return n


def test_nodal_balance_and_dispatch_limits(solved):
    assert check_solution(solved)["passed"]


def test_shutdown_plants_never_generate(solved):
    unavailable = solved.generators.index[solved.generators.p_max_pu == 0]
    assert solved.generators_t.p[unavailable].abs().max().max() < 1e-6
    assert {"garri12", "garri4", "bahri_st", "bahri_gt", "el_fasher"} <= set(unavailable)


def test_shedding_bounded_by_local_hourly_demand(solved):
    for bus in solved.buses.index:
        assert (solved.generators_t.p[f"unserved_{bus}"] <= solved.loads_t.p_set[bus] + 1e-6).all()


def test_hydro_has_finite_energy_and_uses_budget(solved):
    total = solved.generators_t.p.mul(solved.snapshot_weightings.generators, axis=0).sum()
    for plant, budget in solved.meta["hydro_budget_mwh"].items():
        assert total[plant] <= budget + 1e-5
    # Scarce southern hydro must bind, catching accidental omission of the budget.
    assert np.isclose(total["roseires"], solved.meta["hydro_budget_mwh"]["roseires"])


def test_islands_and_reconnection():
    n = build_network()
    g = nx.Graph()
    g.add_nodes_from(n.buses.index)
    g.add_edges_from(n.links.loc[n.links.p_nom > 0, ["bus0", "bus1"]].itertuples(index=False, name=None))
    assert not nx.has_path(g, "Merowe", "Roseires")
    assert not nx.has_path(g, "Nyala", "Merowe")
    repaired = build_network("grid_repair")
    g.add_edges_from(repaired.links.loc[repaired.links.p_nom > 0, ["bus0", "bus1"]].itertuples(index=False, name=None))
    assert nx.has_path(g, "Merowe", "Roseires")
    assert not nx.has_path(g, "Nyala", "Merowe")


def test_demand_normalization_and_nameplate():
    n = build_network()
    buses = pd.read_csv(ROOT / "data/curated/buses.csv").set_index("bus")
    np.testing.assert_allclose(n.loads_t.p_set.mean().loc[buses.index], buses.mean_load_mw)
    physical = ~n.generators.carrier.isin(["unserved", "import"])
    assert np.isclose(n.generators.loc[physical, "p_nom"].sum(), 3647.4)


def test_netcdf_roundtrip_preserves_solution(solved, tmp_path):
    path = tmp_path / "test_network.nc"
    solved.export_to_netcdf(path)
    loaded = pypsa.Network(path)
    np.testing.assert_allclose(loaded.generators_t.p, solved.generators_t.p)
    assert loaded.meta["evidence_date"] == "2024-08"
    assert check_solution(loaded)["passed"]


def test_completed_scenario_direction():
    path = ROOT / "results/scenario_comparison.csv"
    if not path.exists():
        pytest.skip("Run all scenarios to verify comparative statics")
    c = pd.read_csv(path).set_index("scenario")
    if len(c) != 6:
        pytest.skip("Full scenario set is required")
    baseline = c.loc["baseline_2024", "objective_usd"]
    assert c.loc["high_demand", "objective_usd"] >= baseline - 1
    assert c.loc["low_hydro", "objective_usd"] >= baseline - 1
    assert c.loc["weak_transmission", "objective_usd"] >= baseline - 1
    assert c.loc["grid_repair", "objective_usd"] <= baseline + 1
