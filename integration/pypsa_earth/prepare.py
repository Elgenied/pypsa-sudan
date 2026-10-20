"""Export existing Sudan evidence and stage it in an existing PyPSA-Earth checkout.

Run with the activated WSL pypsa-earth environment. No upstream source edits.
Generated plant candidates are deliberately NOT enabled as the complete fleet.
"""
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import subprocess

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
SOURCES = [
    "data/national_coupling/national_2022.csv",
    "results/hourly_supply_requirement.csv",
    "data/report_evidence/plant_inventory_2019.csv",
    "data/report_evidence/plant_status_2024.csv",
    "data/report_evidence/network_evidence.csv",
    "data/report_evidence/scenario_evidence.csv",
    "data/report_evidence/source_register.csv",
    "data/report_evidence/source_issues.csv",
    "data/report_evidence/fuel_prices_2024.csv",
    "data/report_evidence/market_prices_2025.csv",
    "data/report_evidence/import_cost_shares_2025.csv",
    "data/report_evidence/README.md",
    "research/forecasting_2012/data/plant_characteristics.csv",
    "research/forecasting_2012/data/hydro_monthly_long.csv",
    "research/forecasting_2012/data/source_register.csv",
    "data/system_costs/components.csv",
    "data/system_costs/scenario_parameters.csv",
    "data/system_costs/sources.json",
    "research/dre_atlas_2025/data/settlement_attributes.csv.gz",
    "research/dre_atlas_2025/SOURCE_REGISTER.md",
]


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def copy_owned(source, destination, old_hashes):
    """Do not replace a user's modified file on a subsequent staging run."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and digest(source) != digest(destination):
        if old_hashes.get(str(destination)) != digest(destination):
            raise RuntimeError(f"Refusing to overwrite unrecognised changes: {destination}")
    shutil.copy2(source, destination)


def export():
    out = HERE / "generated"
    out.mkdir(exist_ok=True)
    national = pd.read_csv(REPO / SOURCES[0]).set_index("metric")
    metrics = national["value"]
    end_use = float(metrics["consumption"])
    losses = float(metrics["losses"])
    supply = float(metrics["net_generation"] + metrics["imports"])
    assert abs(end_use + losses - supply) < 1e-6
    original = pd.read_csv(REPO / SOURCES[1])
    local = pd.to_datetime(original["local_time"])
    expected = pd.date_range("2022-01-01", "2023-01-01", inclusive="left", freq="h")
    assert len(local) == 8760 and np.array_equal(local.values, expected.values)
    shape = original["supply_requirement_MW"].to_numpy(float)
    assert np.isfinite(shape).all() and (shape > 0).all()
    # Sudan UTC+2: UTC 00:00 takes local 02:00. Wrap two hours at year-end.
    # This is a periodic synthetic profile, not an observation time conversion.
    shape = np.roll(shape, -2)
    shape /= shape.sum()
    demand = pd.DataFrame({
        "region_code": "SD",
        "time": expected,
        "region_name": "Sudan",
        "Electricity demand": shape * supply * 1000,
    })
    demand.to_csv(out / "Africa.csv", sep=";", index=False)
    pd.DataFrame({
        "time_UTC": expected,
        "end_use_MW": shape * end_use * 1000,
        "aggregate_losses_MW": shape * losses * 1000,
        "sent_out_requirement_MW": shape * supply * 1000,
    }).to_csv(out / "demand_accounting.csv", index=False)
    n3 = demand.set_index("time")["Electricity demand"].resample("3h").mean()
    assert len(n3) == 2920 and np.isclose(n3.sum() * 3, supply * 1000)

    inventory = pd.read_csv(REPO / SOURCES[2])
    engineering = pd.read_csv(
        REPO / "research/forecasting_2012/data/plant_characteristics.csv"
    ).set_index("plant_id")
    # Explicit identity crosswalk, not fuzzy matching. Coordinates remain dated.
    matches = {
        "Merowe": "M-HP",
        "Kosti": "Kos-ST",
        "Garri 1 and 2": "G1_B1-2-CCGT2+1",
        "Garri 4": "G4_U1-2-ST",
        "Mahmoud Sharif steam": "KN_3-4-ST",
        "Mahmoud Sharif gas": "KN_0-GT",
        "Roseires": "Ros-HP",
        "Jabal Awlia": "Jeb-HP",
        "Sinnar": "Sen-HP",
        "Khashm El Girba": "KhE-HP",
        "Seitat and Upper Atbara": "UpA-HP",
    }
    inventory["coordinate_record_id"] = inventory.asset_name.map(matches)
    inventory["latitude"] = inventory.coordinate_record_id.map(engineering.latitude)
    inventory["longitude"] = inventory.coordinate_record_id.map(engineering.longitude)
    inventory["coordinate_source"] = np.where(
        inventory.latitude.notna(), "MWRE_Lahmeyer_2012_260690 PDF p120", ""
    )
    inventory["integration_status"] = np.select(
        [inventory.category.eq("pipeline"), inventory.latitude.isna()],
        ["exclude_planned_not_verified_commissioned", "review_missing_coordinates"],
        default="candidate_only_reconcile_2022_net_capacity_and_identity",
    )
    inventory.to_csv(out / "plant_evidence_crosswalk.csv", index=False)
    candidates = []
    for row in inventory.loc[inventory.coordinate_record_id.notna()].itertuples():
        is_hydro = row.technology == "Hydro"
        candidates.append({
            "Name": row.asset_name,
            "Fueltype": "Hydro" if is_hydro else ("Coal" if row.asset_name == "Garri 4" else "Oil"),
            "Technology": "Reservoir" if is_hydro else row.technology,
            "Set": "PP", "Country": "Sudan", "Capacity": row.installed_capacity_MW,
            "Efficiency": np.nan, "Duration": np.nan, "Volume_Mm3": np.nan,
            "DamHeight_m": np.nan, "StorageCapacity_MWh": np.nan,
            "DateIn": np.nan, "DateRetrofit": np.nan, "DateOut": np.nan,
            "lat": row.latitude, "lon": row.longitude, "EIC": np.nan,
            "projectID": row.record_id, "bus": np.nan,
        })
    # Explicit index: upstream add_custom_powerplants reads index_col=0.
    pd.DataFrame(candidates).to_csv(out / "powerplants_CANDIDATE_ONLY.csv", index_label="id")
    meta = {
        "status": "input_integration_not_a_solved_or_validated_national_model",
        "demand": {
            "source": SOURCES[1], "profile_evidence": "synthetic",
            "annual_reference": SOURCES[0], "clock": "UTC",
            "clock_conversion": "local UTC+2 cyclic shift of synthetic annual template",
            "end_use_GWh": end_use, "aggregate_losses_GWh": losses,
            "sent_out_requirement_GWh": supply,
            "loss_boundary": "Includes technical and nontechnical T&D losses; no additional loss factor.",
            "source_reader": "gegis is the native CSV reader, NOT the provenance",
            "hourly_steps": 8760, "three_hour_steps": 2920,
        },
        "plants": {
            "review_rows": len(inventory), "format_candidates": len(candidates),
            "enabled": False,
            "reason": "Incomplete fleet; nameplate not net MW; dated coordinates and fuel/technology mappings need reconciliation.",
            "special_cases": [
                "Kosti and Upper Atbara coordinates were planning entries in 2012; 2019 inventory reports plants.",
                "Garri 4 Coal is a provisional Earth carrier mapping for sponge coke; not verified fuel equivalence.",
                "Hydro Reservoir labels need engineering verification; no reservoir energy capacity inferred.",
                "No 2012 planned retirement dates or 2019 year-as-printed values imported as verified dates.",
            ],
        },
        "national_imports_GWh": float(metrics["imports"]),
        "imports_status": "validation target only; not yet represented by border supply in the SD-only Earth network",
        "six_state_access_focus": ["Northern", "River Nile", "Khartoum", "Gezira", "White Nile", "Sennar"],
        "sources": [{"path": p, "sha256": digest(REPO / p)} for p in SOURCES],
    }
    (out / "evidence_manifest.json").write_text(json.dumps(meta, indent=2) + "\n")
    return out


def stage(earth):
    earth = earth.expanduser().resolve()
    if not (earth / "Snakefile").is_file():
        raise ValueError(f"Not a PyPSA-Earth checkout: {earth}")
    out = export()
    install = earth / "data/custom/sudan"
    receipt = install / "installation.json"
    old = json.loads(receipt.read_text())["installed_hashes"] if receipt.exists() else {}
    copies = [(REPO / p, install / "evidence" / p) for p in SOURCES]
    copies += [(p, install / p.name) for p in out.iterdir() if p.is_file()]
    copies += [(HERE / "config.sudan-2022.yaml", earth / "configs/config.sudan-2022.yaml"),
               (out / "Africa.csv", earth / "data/ssp2-2.6/2022/era5_2022/Africa.csv")]
    for src, dest in copies:
        copy_owned(src, dest, old)
    receipt.write_text(json.dumps({
        "earth_root": str(earth),
        "earth_commit": subprocess.check_output(["git", "-C", str(earth), "rev-parse", "HEAD"], text=True).strip(),
        "installed_hashes": {str(dest): digest(dest) for _, dest in copies},
    }, indent=2) + "\n")
    print(f"Staged {len(copies)} files in {earth}; original config.yaml is unchanged.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--earth", type=Path)
    args = parser.parse_args()
    if args.earth:
        stage(args.earth)
    else:
        print(export())
