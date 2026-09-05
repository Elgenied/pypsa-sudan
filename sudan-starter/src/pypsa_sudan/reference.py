"""2022 national annual calibration benchmark; separate from the legacy 2024 grid."""
from pathlib import Path
import hashlib
import importlib.metadata
import json

import numpy as np
import pandas as pd
import pypsa

ROOT = Path(__file__).resolve().parents[2]


def read_reference(root=ROOT):
    root = Path(root)
    cfg = json.loads((root / "config/reference_2022.json").read_text())
    table = pd.read_csv(root / "data/reference/unsd_2022/statistics.csv")
    assert table.metric.is_unique
    s = table.set_index("metric").value.to_dict()
    assert cfg["reference_year"] == 2022
    assert np.isclose(s["capacity_total"], sum(s[f"capacity_{c}"] for c in ["hydro", "combustible", "other"]))
    assert np.isclose(s["gross_generation"] - s["plant_own_use"], s["net_generation"])
    # Exports are missing, not an observed zero. Zero is a balance-closing assumption.
    assert np.isclose(s["net_generation"] + s["imports"], s["consumption"] + s["losses"])
    assert abs(sum(s[f"gross_{c}"] for c in ["hydro", "combustible", "other"]) - s["gross_generation"]) <= 1.01
    return cfg, s


def build_reference(root=ROOT):
    cfg, s = read_reference(root)
    n = pypsa.Network()
    n.name = "Sudan 2022 national annual calibration benchmark"
    n.set_snapshots(pd.date_range("2022-01-01", "2023-01-01", inclusive="left", freq="h"))
    n.snapshot_weightings.loc[:, :] = 1.0
    hours = len(n.snapshots)
    for carrier in ["AC", "hydro", "combustible", "other", "import", "unserved"]:
        n.add("Carrier", carrier)
    n.add("Bus", "Sudan", carrier="AC", unit="MW")
    # Gross categories sum to 16772 GWh, one above the published rounded total.
    # Allocate national net output proportionally; neither net technology outputs
    # nor technology-specific auxiliary losses are observations in this table.
    gross_sum = sum(s[f"gross_{c}"] for c in ["hydro", "combustible", "other"])
    net_targets = {c: s[f"gross_{c}"] / gross_sum * s["net_generation"] * 1000 for c in ["hydro", "combustible", "other"]}
    h = n.snapshots.hour.to_numpy()
    shape = 0.80 + 0.18 * np.exp(-((h - 15) / 4) ** 2) + 0.40 * np.exp(-((h - 21) / 3) ** 2)
    shape /= shape.mean()
    # Consumption is supplied energy, not unconstrained/latent demand.
    for name, metric in [("supplied_consumption", "consumption"), ("system_losses", "losses")]:
        n.add("Load", name, bus="Sudan", p_set=shape * s[metric] * 1000 / hours * cfg["demand_scale"])
    for c in ["hydro", "combustible", "other"]:
        n.add("Generator", c, bus="Sudan", carrier=c, p_nom=s[f"capacity_{c}"], marginal_cost=cfg["marginal_cost_usd_mwh"][c])
    # Other stays aggregated; a flat allocation is not a solar/weather profile.
    other_pu = net_targets["other"] / hours / s["capacity_other"]
    n.generators.loc["other", ["p_min_pu", "p_max_pu"]] = other_pu
    # This p_nom is an accounting placeholder for a fixed average flow, not a rating.
    n.add("Generator", "imports", bus="Sudan", carrier="import", p_nom=s["imports"] * 1000 / hours, p_min_pu=1, p_max_pu=1, marginal_cost=cfg["marginal_cost_usd_mwh"]["import"])
    demand = n.loads_t.p_set.sum(axis=1)
    n.add("Generator", "unserved", bus="Sudan", carrier="unserved", p_nom=float(demand.max()), p_max_pu=demand / demand.max(), marginal_cost=cfg["marginal_cost_usd_mwh"]["unserved"])
    n.meta = {"reference_year": 2022, "config": cfg, "statistics": s,
              "net_generation_targets_mwh": net_targets,
              "hydro_budget_mwh": net_targets["hydro"] * cfg["hydro_energy_scale"],
              "exports_assumption_gwh": 0,
              "gross_category_rounding_difference_gwh": gross_sum - s["gross_generation"]}
    return n


def annual_hydro_constraint(n, snapshots):
    weight = n.snapshot_weightings.generators.loc[snapshots].to_xarray()
    hydro = n.model.variables["Generator-p"].sel(name="hydro")
    n.model.add_constraints((hydro * weight).sum() <= n.meta["hydro_budget_mwh"], name="AnnualHydroEnergy")


def validate_reference(n):
    p = n.generators_t.p
    demand = n.loads_t.p_set.sum(axis=1)
    upper = n.get_switchable_as_dense("Generator", "p_max_pu") * n.generators.p_nom
    lower = n.get_switchable_as_dense("Generator", "p_min_pu") * n.generators.p_nom
    energy = p.mul(n.snapshot_weightings.generators, axis=0).sum()
    errors = {
        "balance_mw": float((p.sum(axis=1) - demand).abs().max()),
        "generator_upper_mw": max(0., float((p - upper).max().max())),
        "generator_lower_mw": max(0., float((lower - p).max().max())),
        "hydro_budget_mwh": max(0., float(energy.hydro - n.meta["hydro_budget_mwh"])),
        "unserved_bound_mw": max(0., float((p.unserved - demand).max())),
        "imports_mwh": abs(float(energy.imports - n.meta["statistics"]["imports"] * 1000)),
    }
    assert max(errors.values()) < 1e-4, errors
    objective_error = abs(float((energy * n.generators.marginal_cost).sum()) - n.objective)
    assert objective_error < 0.1
    return {"passed": True, "errors": errors, "objective_error_usd": objective_error,
            "interpretation": "Numerical/accounting checks, not independent empirical validation."}


def run_reference(root=ROOT):
    root = Path(root)
    n = build_reference(root)
    out = root / "results/reference_2022"
    out.mkdir(parents=True, exist_ok=True)
    status, condition = n.optimize(solver_name="highs", extra_functionality=annual_hydro_constraint,
                                  solver_options={"threads": 1, "random_seed": 0})
    if (status, condition) != ("ok", "optimal"):
        raise RuntimeError((status, condition))
    qa = validate_reference(n)
    energy = n.generators_t.p.mul(n.snapshot_weightings.generators, axis=0).sum()
    n.export_to_netcdf(out / "network.nc")
    n.generators_t.p.to_csv(out / "dispatch_mw.csv")
    n.loads_t.p_set.to_csv(out / "loads_mw.csv")
    comparison = pd.DataFrame({"derived_net_target_mwh": n.meta["net_generation_targets_mwh"]})
    comparison["model_mwh"] = energy.reindex(comparison.index)
    comparison["difference_mwh"] = comparison.model_mwh - comparison.derived_net_target_mwh
    comparison.to_csv(out / "calibration_comparison.csv")
    summary = {"reference_year": 2022, "status": "optimal", "hours": len(n.snapshots), "buses": 1,
               "net_installed_capacity_mw": float(n.generators.loc[["hydro", "combustible", "other"], "p_nom"].sum()),
               "net_generation_mwh": float(energy[["hydro", "combustible", "other"]].sum()),
               "imports_mwh": float(energy.imports), "unserved_mwh": float(energy.unserved),
               "loads_mwh": n.loads_t.p_set.sum().to_dict(), "dispatch_energy_mwh": energy.to_dict(),
               "illustrative_objective_usd": float(n.objective), "warning": n.meta["config"]["warning"]}
    paths = [root / "config/reference_2022.json", root / "data/reference/unsd_2022/statistics.csv", Path(__file__)]
    manifest = {"packages": {p: importlib.metadata.version(p) for p in ["pypsa", "linopy", "highspy", "pandas", "numpy"]},
                "input_sha256": {str(p.relative_to(root)).replace("\\", "/"): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}}
    for name, content in [("summary", summary), ("validation", qa), ("run_manifest", manifest)]:
        (out / f"{name}.json").write_text(json.dumps(content, indent=2), encoding="utf-8")
    print(f"2022: {len(n.snapshots)} hours, {summary['net_generation_mwh']/1000:.1f} GWh net domestic generation; numerical checks passed.")
    return n
