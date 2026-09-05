"""Lossless multi-region economic dispatch, with explicit assumptions and QA."""
from pathlib import Path
import argparse
import hashlib
import importlib.metadata
import json
import logging
import platform
import sys
import time

import numpy as np
import pandas as pd
import pypsa

ROOT = Path(__file__).resolve().parents[2]


def read_inputs(root=ROOT):
    root = Path(root)
    config = json.loads((root / "config/model.json").read_text())
    scenarios = json.loads((root / "config/scenarios.json").read_text())
    tables = {name: pd.read_csv(root / f"data/curated/{name}.csv") for name in ["buses", "plants", "corridors", "imports"]}
    return config, scenarios, tables


def validate_inputs(config, tables):
    b, p, c, imp = (tables[k] for k in ["buses", "plants", "corridors", "imports"])
    assert b.bus.is_unique and p.plant_id.is_unique and c.corridor.is_unique
    assert (b.mean_load_mw >= 0).all() and b.mean_load_mw.sum() > 0
    assert (p.p_nom_mw > 0).all() and (c.transfer_mw > 0).all()
    assert set(p.bus) | set(c.bus0) | set(c.bus1) | set(imp.bus) <= set(b.bus)
    assert (c.bus0 != c.bus1).all()
    assert c.baseline_active.isin([0, 1]).all()
    known = p.available_mw_2024.notna()
    assert (p.loc[known, "available_mw_2024"] >= 0).all()
    assert (p.loc[known, "available_mw_2024"] <= p.loc[known, "p_nom_mw"]).all()
    assert 0 <= config["partial_diesel_availability_assumption"] <= 1
    assert 0 < config["hydro_energy_capacity_factor"] <= 1
    assert config["hours"] > 0
    assert config["load_shedding_cost_usd_per_mwh"] > max(p.marginal_cost_usd_mwh.max(), imp.marginal_cost_usd_mwh.max())


def synthetic_load(snapshots, buses, scale):
    """Deterministic shape; each bus mean equals its explicit assumption exactly."""
    h = snapshots.hour.to_numpy()
    # Evening maximum and a smaller afternoon peak, with a gentle weekly effect.
    shape = 0.80 + 0.18 * np.exp(-((h - 15) / 4) ** 2) + 0.40 * np.exp(-((h - 21) / 3) ** 2)
    shape *= np.where(snapshots.dayofweek.to_numpy() >= 4, 0.97, 1.0)
    shape /= shape.mean()
    return pd.DataFrame(np.outer(shape, buses.mean_load_mw.to_numpy() * scale), index=snapshots, columns=buses.bus)


def build_network(scenario="baseline_2024", root=ROOT, hours=None):
    cfg, cases, tables = read_inputs(root)
    if hours is not None:
        cfg["hours"] = hours
    validate_inputs(cfg, tables)
    case = cases[scenario]
    n = pypsa.Network()
    n.name = f"PyPSA-Sudan {scenario}: preliminary transport dispatch"
    n.set_snapshots(pd.date_range(cfg["start"], periods=cfg["hours"], freq="h"))
    n.snapshot_weightings.loc[:, :] = 1.0  # Each snapshot is one actual model hour.
    colors = {"AC": "#45556c", "hydro": "#2289ae", "oil": "#cf8950", "coal": "#6b7280", "diesel": "#8b5e3c", "import": "#7c69b5", "unserved": "#df4c4c", "transport": "#6d7f91"}
    for carrier, color in colors.items():
        n.add("Carrier", carrier, color=color, nice_name=carrier.title())
    for b in tables["buses"].itertuples(index=False):
        n.add("Bus", b.bus, x=b.longitude, y=b.latitude, carrier="AC", unit="MW")
    demand = synthetic_load(n.snapshots, tables["buses"], case["demand_scale"])
    for b in tables["buses"].itertuples(index=False):
        n.add("Load", b.bus, bus=b.bus, p_set=demand[b.bus])
        peak = float(demand[b.bus].max())
        n.add("Generator", f"unserved_{b.bus}", bus=b.bus, carrier="unserved", p_nom=peak, p_max_pu=demand[b.bus] / peak if peak else 0.0, marginal_cost=cfg["load_shedding_cost_usd_per_mwh"])
    budgets = {}
    for p in tables["plants"].itertuples(index=False):
        available = p.available_mw_2024
        if pd.isna(available):
            available = p.p_nom_mw * cfg["partial_diesel_availability_assumption"]
        if case["thermal_recovery"] and p.carrier != "hydro":
            available = 0.70 * p.p_nom_mw
        n.add("Generator", p.plant_id, bus=p.bus, carrier=p.carrier, p_nom=p.p_nom_mw, p_max_pu=available / p.p_nom_mw, marginal_cost=p.marginal_cost_usd_mwh)
        if p.carrier == "hydro":
            budgets[p.plant_id] = float(available * cfg["hours"] * cfg["hydro_energy_capacity_factor"] * case["hydro_scale"])
    for p in tables["imports"].itertuples(index=False):
        n.add("Generator", p.name, bus=p.bus, carrier="import", p_nom=p.p_nom_mw, marginal_cost=p.marginal_cost_usd_mwh)
    for c in tables["corridors"].itertuples(index=False):
        active = bool(c.baseline_active) or case["repair_grid"]
        cap = c.transfer_mw * case["transfer_scale"] if active else 0.0
        # Bidirectional lossless transport link. No impedances / KVL are invented.
        n.add("Link", c.corridor, bus0=c.bus0, bus1=c.bus1, carrier="transport", p_nom=cap, p_min_pu=-1.0, efficiency=1.0)
    n.meta = {"scenario": scenario, "case": case, "config": cfg, "hydro_budget_mwh": budgets, "evidence_date": cfg["evidence_date"], "limitations": cfg["warning"]}
    return n


def hydro_constraints(n, snapshots):
    p = n.model.variables["Generator-p"]
    # Explicit energy constraint, weighted with the same hours as reported energy.
    weight = n.snapshot_weightings.generators.loc[snapshots].to_xarray()
    for name, limit in n.meta["hydro_budget_mwh"].items():
        n.model.add_constraints((p.sel(name=name) * weight).sum() <= limit, name=f"HydroEnergy-{name}")


def check_solution(n, tolerance=1e-5):
    p = n.generators_t.p
    demand = n.loads_t.p_set
    balance = pd.DataFrame(0.0, index=n.snapshots, columns=n.buses.index)
    for name, g in n.generators.iterrows():
        balance[g.bus] += p[name]
    for name, load in n.loads.iterrows():
        balance[load.bus] -= demand[name]
    for name, link in n.links.iterrows():
        balance[link.bus0] -= n.links_t.p0[name]
        balance[link.bus1] -= n.links_t.p1[name]
    residual = float(balance.abs().to_numpy().max())
    gen_upper = n.get_switchable_as_dense("Generator", "p_max_pu") * n.generators.p_nom
    upper_violation = float((p - gen_upper).to_numpy().max())
    flow_violation = float((n.links_t.p0.abs() - n.links.p_nom).to_numpy().max())
    energy = p.mul(n.snapshot_weightings.generators, axis=0).sum()
    hydro_violation = max(float(energy[name] - limit) for name, limit in n.meta["hydro_budget_mwh"].items())
    assert residual < tolerance, f"Nodal energy balance residual {residual}"
    assert upper_violation < tolerance and p.to_numpy().min() >= -tolerance
    assert flow_violation < tolerance and hydro_violation < tolerance
    # Load shedding must remain separately measurable and cannot exceed local demand.
    for b in n.buses.index:
        assert (p[f"unserved_{b}"] - demand[b]).max() < tolerance
    real_cost = float((energy * n.generators.marginal_cost).sum())
    assert np.isclose(real_cost, n.objective, atol=0.1, rtol=1e-8)
    return {"passed": True, "max_nodal_balance_error_mw": residual, "max_generator_upper_violation_mw": max(0.0, upper_violation), "max_transfer_violation_mw": max(0.0, flow_violation), "max_hydro_energy_violation_mwh": max(0.0, hydro_violation), "objective_recalculation_error_usd": abs(real_cost - n.objective)}


def export_results(n, folder):
    folder.mkdir(parents=True, exist_ok=True)
    qa = check_solution(n)
    n.export_to_netcdf(folder / "network.nc")
    energy = n.generators_t.p.mul(n.snapshot_weightings.generators, axis=0).sum()
    by_carrier = n.generators_t.p.T.groupby(n.generators.carrier).sum().T
    by_carrier.to_csv(folder / "dispatch_by_carrier_mw.csv")
    n.generators_t.p.to_csv(folder / "dispatch_by_generator_mw.csv")
    n.loads_t.p_set.to_csv(folder / "demand_mw.csv")
    n.links_t.p0.to_csv(folder / "corridor_flows_mw.csv")
    n.buses_t.marginal_price.to_csv(folder / "nodal_marginal_cost_usd_mwh.csv")
    assets = n.generators.copy()
    assets["generation_mwh"] = energy
    assets["capacity_factor_over_model_horizon"] = energy / (assets.p_nom * n.snapshot_weightings.generators.sum())
    assets.to_csv(folder / "generators_summary.csv")
    regional = pd.DataFrame(index=n.buses.index)
    regional["demand_mwh"] = n.loads_t.p_set.mul(n.snapshot_weightings.generators, axis=0).sum()
    regional["unserved_mwh"] = [energy[f"unserved_{b}"] for b in regional.index]
    regional["unserved_fraction"] = regional.unserved_mwh / regional.demand_mwh
    regional.to_csv(folder / "regional_service.csv")
    demand_mwh = float(regional.demand_mwh.sum())
    ens = float(regional.unserved_mwh.sum())
    unserved = n.generators.carrier == "unserved"
    imports = n.generators.carrier == "import"
    summary = {"scenario": n.meta["scenario"], "status": "optimal", "hours": len(n.snapshots), "domestic_buses": len(n.buses), "physical_plant_records": int((~(unserved | imports)).sum()), "domestic_nameplate_mw": float(n.generators.loc[~(unserved | imports), "p_nom"].sum()), "demand_mwh": demand_mwh, "peak_demand_mw": float(n.loads_t.p_set.sum(axis=1).max()), "served_mwh": demand_mwh - ens, "unserved_mwh": ens, "unserved_percent": 100 * ens / demand_mwh, "hours_with_unserved_demand": int((by_carrier.unserved > 1e-5).sum()), "import_mwh": float(energy[imports].sum()), "operating_cost_usd": float((energy[~unserved] * n.generators.loc[~unserved, "marginal_cost"]).sum()), "unserved_penalty_usd": float((energy[unserved] * n.generators.loc[unserved, "marginal_cost"]).sum()), "objective_usd": float(n.objective), "warning": n.meta["limitations"]}
    (folder / "summary.json").write_text(json.dumps(summary, indent=2))
    (folder / "validation.json").write_text(json.dumps(qa, indent=2))
    return summary


def run(scenarios=None, root=ROOT, hours=None):
    root = Path(root)
    _, cases, _ = read_inputs(root)
    selected = list(cases) if scenarios is None else scenarios
    (root / "results").mkdir(exist_ok=True)
    versions = {p: importlib.metadata.version(p) for p in ["pypsa", "linopy", "highspy", "pandas", "numpy", "xarray", "geopandas"]}
    run_meta = {"python": sys.version, "platform": platform.platform(), "packages": versions, "input_sha256": {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for directory in ["config", "data/curated", "src/pypsa_sudan"] for p in (root / directory).glob("*") if p.is_file()}, "scenario_results": []}
    for scenario in selected:
        started = time.perf_counter()
        n = build_network(scenario, root, hours)
        folder = root / "results" / scenario
        folder.mkdir(parents=True, exist_ok=True)
        status, condition = n.optimize(solver_name="highs", extra_functionality=hydro_constraints, solver_options={"threads": 1, "random_seed": 0, "log_file": str(folder / "highs.log")})
        if status != "ok" or condition != "optimal":
            raise RuntimeError(f"{scenario}: {status}, {condition}")
        summary = export_results(n, folder)
        summary["solve_and_export_seconds"] = time.perf_counter() - started
        run_meta["scenario_results"].append(summary)
        print(f"{scenario}: demand {summary['demand_mwh']/1000:.2f} GWh; unmet {summary['unserved_percent']:.2f}%")
    pd.DataFrame(run_meta["scenario_results"]).to_csv(root / "results/scenario_comparison.csv", index=False)
    (root / "results/run_manifest.json").write_text(json.dumps(run_meta, indent=2))
    return run_meta


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", choices=list(read_inputs()[1]) + ["all"], default="all")
    parser.add_argument("--hours", type=int, default=None, help="Override model horizon; synthetic profile is normalized over this horizon")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    run(None if args.scenario == "all" else [args.scenario], hours=args.hours)


if __name__ == "__main__":
    main()
