"""Reproducible six-state OnSSET screening linked to saved PyPSA recovery cases.

Run with the project's PyPSA environment. OnSSET is fetched at a pinned commit
into an ignored local cache; it is not installed into the Conda environment.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"
ONSSET_COMMIT = "486c26039ecbf8614d68da90c7b4968b2f4a5b13"
ONSSET_URL = "https://github.com/OnSSET/onsset.git"
STATES = ("Northern", "River Nile", "Khartoum", "Gezira", "White Nile", "Sennar")
CASES = {
    "restricted": "restricted_mixed_36_d1_f1",
    "selective": "selective_mixed_36_d1_f1",
    "restored": "restored_mixed_36_d1_f1",
}
COLORS = {"grid": "#4269A5", "mini_grid": "#24988B", "standalone": "#DEA83C"}


def load_onsset():
    cache = HERE / ".cache" / "onsset"
    if not cache.exists():
        cache.mkdir(parents=True)
        subprocess.run(["git", "init", "-q", str(cache)], check=True)
        subprocess.run(["git", "-C", str(cache), "remote", "add", "origin", ONSSET_URL], check=True)
    head = subprocess.run(["git", "-C", str(cache), "rev-parse", "HEAD"],
                          capture_output=True, text=True)
    if head.returncode or head.stdout.strip() != ONSSET_COMMIT:
        subprocess.run(["git", "-C", str(cache), "fetch", "-q", "--depth", "1", "origin", ONSSET_COMMIT], check=True)
        subprocess.run(["git", "-C", str(cache), "checkout", "-q", "--detach", "FETCH_HEAD"], check=True)
    sys.path.insert(0, str(cache))
    from onsset import Technology
    return Technology


def inputs():
    atlas = pd.read_csv(ROOT / "research/dre_atlas_2025/data/settlement_attributes.csv.gz")
    atlas = atlas.loc[atlas.admin_cgaz_1.isin(STATES)].copy()
    crosswalk = pd.read_csv(ROOT / "data/regional_model/crosswalk_36.csv.gz")
    atlas = atlas.merge(crosswalk[["geohash", "zone_id", "supply_bus"]], on="geohash", validate="one_to_one")
    assert len(atlas) == 11268 and atlas.geohash.is_unique
    assert atlas[["population", "num_connections", "demand", "hull_area"]].notna().all().all()
    assert (atlas[["population", "num_connections", "demand", "hull_area"]] > 0).all().all()
    atlas["annual_kWh"] = np.maximum(atlas.demand, atlas.num_connections) * 365.0
    atlas["service_floor_applied"] = atlas.demand < atlas.num_connections
    atlas["effective_people_per_connection"] = atlas.population / atlas.num_connections
    # This is a building-to-potential-connection conversion, not a measured household size.
    atlas["grid_distance_km"] = atlas.distance_to_existing_transmission_lines.clip(lower=0)
    return atlas


def case_register():
    directory = ROOT / "research/regional_joint_study/results"
    summary = pd.read_csv(directory / "summary.csv").set_index("case")
    repairs = pd.read_csv(directory / "all_repairs.csv")
    scenarios = json.loads((ROOT / "data/regional_model/config.json").read_text())["scenarios"]
    rows = []
    for condition, case in CASES.items():
        s = summary.loc[case]
        r = repairs.loc[(repairs.case == case) & (repairs.selected == 1)]
        outage_hours = len(scenarios[condition]["outage_local_hours"])
        rows.append({"condition": condition, "pypsa_case": case,
                     "outage_hours_per_day_assumed": outage_hours,
                     "outage_energy_share_proxy": outage_hours / 24,
                     "selected_repairs": "; ".join(r.asset_id),
                     "repair_initial_USD": float(r.spend_USD.sum()),
                     "pypsa_annual_system_cost_USD": float(s.annual_system_cost_USD),
                     "pypsa_unserved_MWh": float(s.unserved_MWh)})
    return pd.DataFrame(rows)


def lcoe_options(atlas, Technology):
    # Indicative 2022-USD screening costs. Supply component anchors:
    # data/system_costs/{components,scenario_parameters}.csv. Combined PV/battery
    # $/kW packages are explicit simplified proxies, not supplier quotations.
    Technology.set_default_values(base_year=2022, start_year=2025, end_year=2044)
    common = dict(discount_rate=0.10, mv_line_cost=20000, lv_line_cost=10000,
                  service_transf_cost=12000, service_transf_type=100,
                  connection_cost_per_hh=120, distribution_losses=0.08)
    class VectorizedStandalone(Technology):
        """Broadcast an upstream scalar-zero T&D result to settlement row count.

        OnSSET 486c260's standalone T&D is exactly zero; its scalar output
        otherwise makes get_lcoe create a one-row capital-cost Series.
        """

        def td_network_cost(self, people, *args, **kwargs):
            parts = list(super().td_network_cost(people, *args, **kwargs))
            if np.isscalar(parts[2]):
                parts[2] = np.zeros(len(people))
            return tuple(parts)

    techs = {
        "grid": Technology(tech_life=30, capital_cost={float("inf"): 0},
                           capacity_factor=0.9, grid_price=0.15, om_costs=0.02,
                           mv_line_max_length=50, **common),
        "mini_grid": Technology(tech_life=20, capital_cost={float("inf"): 3000},
                                capacity_factor=0.40, om_costs=0.04,
                                mini_grid=True, **common),
        "standalone": VectorizedStandalone(tech_life=15, capital_cost={float("inf"): 4000},
                                 capacity_factor=0.25, om_costs=0.03,
                                 standalone=True, distribution_losses=0,
                                 **{k: v for k, v in common.items() if k != "distribution_losses"}),
    }
    result = atlas[["geohash", "admin_cgaz_1", "zone_id", "supply_bus", "lat", "lon",
                    "population", "num_connections", "annual_kWh", "grid_distance_km",
                    "security_risk", "service_floor_applied"]].copy()
    people = atlas.population.reset_index(drop=True)
    ppconn = atlas.effective_people_per_connection.reset_index(drop=True)
    connections = atlas.num_connections.reset_index(drop=True)
    energy = atlas.annual_kWh.reset_index(drop=True)
    area = atlas.hull_area.reset_index(drop=True)
    for mode, tech in techs.items():
        distance = atlas.grid_distance_km.reset_index(drop=True) if mode == "grid" else 0.0
        lcoe, investment, capacity = tech.get_lcoe(
            energy_per_cell=energy, people=people, num_people_per_hh=ppconn,
            start_year=2025, end_year=2044, new_connections=connections,
            total_energy_per_cell=energy, prev_code=99, grid_cell_area=area,
            base_to_peak_load_ratio=0.5, additional_mv_line_length=distance,
            capacity_factor=tech.capacity_factor)
        result[f"{mode}_lcoe_USD_kWh"] = lcoe[0].to_numpy()
        result[f"{mode}_investment_USD"] = investment[0].to_numpy()
        result[f"{mode}_capacity_kW"] = capacity[0].to_numpy()
    # An unknown/mixed-voltage line within 50 km is only a connection candidate,
    # never proof that an MV feeder or spare transmission capacity exists.
    result.loc[result.grid_distance_km > 50, "grid_lcoe_USD_kWh"] = np.inf
    return result


def main():
    Technology = load_onsset()
    atlas = inputs()
    options = lcoe_options(atlas, Technology)
    cases = case_register()
    all_results = []
    for row in cases.itertuples(index=False):
        table = options.copy()
        table["condition"] = row.condition
        # The native OnSSET grid LCOE purchases all electricity at the ledger's
        # bulk-supply price. Replace the assumed outage-energy fraction with an
        # explicit $0.45/kWh reliable backup supply proxy; no actual outage data.
        table["grid_reliable_lcoe_USD_kWh"] = (
            table.grid_lcoe_USD_kWh + row.outage_energy_share_proxy * (0.45 - 0.15))
        cols = ["grid_reliable_lcoe_USD_kWh", "mini_grid_lcoe_USD_kWh", "standalone_lcoe_USD_kWh"]
        values = table[cols].to_numpy()
        table["screen_choice"] = np.array(["grid", "mini_grid", "standalone"])[np.argmin(values, axis=1)]
        table["selected_lcoe_USD_kWh"] = values.min(axis=1)
        table["indicative_annual_service_cost_USD"] = table.selected_lcoe_USD_kWh * table.annual_kWh
        all_results.append(table)
    result = pd.concat(all_results, ignore_index=True)
    assert len(result) == len(atlas) * len(CASES)
    assert np.isfinite(result.selected_lcoe_USD_kWh).all()
    assert (result.selected_lcoe_USD_kWh > 0).all()
    state = (result.groupby(["condition", "admin_cgaz_1", "screen_choice"], observed=True)
             .agg(settlements=("geohash", "size"), potential_connections=("num_connections", "sum"),
                  annual_kWh=("annual_kWh", "sum"),
                  indicative_annual_service_cost_USD=("indicative_annual_service_cost_USD", "sum"))
             .reset_index())
    counts = result.pivot(index="geohash", columns="condition", values="screen_choice")
    changes = int((counts.restricted != counts.restored).sum())
    manifest = {
        "onsset_commit": ONSSET_COMMIT, "source_clusters": len(atlas),
        "atlas_population_type": "VIDA/GHSL modeled, not a census",
        "connection_type": "buildings >=15m2, not metered customers",
        "demand_type": "DRE atlas low-service synthetic demand; raised to 1 kWh/day per potential connection",
        "observed_access_status": False, "observed_war_damage": False,
        "grid_line_voltage_verified": False, "hourly_local_reliability_verified": False,
        "screen_only": True, "restricted_to_restored_switches": changes,
        "grid_max_distance_km": 50, "backup_energy_price_USD_kWh": 0.45,
        "onsset_options": ["grid", "mini_grid", "standalone"],
    }
    RESULTS.mkdir(exist_ok=True)
    result.to_csv(RESULTS / "settlement_screen.csv.gz", index=False, compression="gzip")
    state.to_csv(RESULTS / "state_summary.csv", index=False)
    cases.to_csv(RESULTS / "pypsa_case_register.csv", index=False)
    (RESULTS / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"clusters": len(atlas), "rows": len(result), "switches": changes,
                      "choices": result.groupby(["condition", "screen_choice"]).size().unstack(fill_value=0).to_dict()},
                     indent=2))


if __name__ == "__main__":
    main()
