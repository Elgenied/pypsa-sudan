"""Compatibility and data-boundary checks against the actual installed engine."""
from pathlib import Path
import argparse
import hashlib
import importlib.metadata
import json
import os
import subprocess
import sys

import numpy as np
import pandas as pd
import pypsa
import yaml
from snakemake.utils import update_config

HERE = Path(__file__).resolve().parent


def main(earth):
    earth = earth.expanduser().resolve()
    os.chdir(earth)
    sys.path.insert(0, str(earth / "scripts"))
    from _helpers import update_cutout_config
    from build_demand_profiles import compose_gegis_load, get_load_paths_gegis
    from build_powerplants import add_custom_powerplants
    from prepare_network import average_every_nhours
    from pyproj import CRS
    import highspy

    config = {}
    for file in [
        "config.default.yaml", "configs/plotting.default.yaml",
        "configs/solving.default.yaml", "configs/bundle_config.yaml",
        "configs/powerplantmatching_config.yaml", "config.yaml",
        "configs/config.sudan-2022.yaml",
    ]:
        update_config(config, yaml.safe_load((earth / file).read_text()) or {})
    config = update_cutout_config(config)
    assert config["countries"] == ["SD"] and not config["tutorial"]
    assert config["scenario"]["opts"] == ["3H"]
    assert config["scenario"]["ll"] == ["c1.0"]
    assert config["scenario"]["clusters"] == [10]
    assert config["solving"]["solver"]["name"] == "highs"
    assert not config["electricity"]["custom_powerplants"]["method"]
    assert config["electricity"]["renewable_carriers"] == ["solar", "onwind", "hydro"]
    assert config["renewable"]["hydro"]["hydrobasins_level"] == 6
    assert config["renewable"]["hydro"]["resource"]["hydrobasins"] == "data/hydrobasins/hybas_world.shp"
    assert not config["co2"]["automatic_emission"]["enable"]
    assert config["enable"]["build_cutout"] and not config["enable"]["retrieve_cutout"]
    assert CRS.from_epsg(4326).to_epsg() == 4326
    paths = get_load_paths_gegis("data", config)
    assert paths == ["data/ssp2-2.6/2022/era5_2022/Africa.csv"], paths
    load = compose_gegis_load(paths, ["SD"])
    assert len(load) == 8760 and load.index.is_unique
    assert load.index.equals(pd.date_range("2022-01-01", "2023-01-01", inclusive="left", freq="h"))
    assert np.isclose(load["Electricity demand"].sum(), 16_913_000)
    # Use the engine's own aggregation function, not only a parallel calculation.
    n = pypsa.Network()
    n.set_snapshots(load.index)
    n.add("Bus", "SD")
    n.add("Load", "national_proxy", bus="SD", p_set=load["Electricity demand"])
    aggregated = average_every_nhours(n, "3H")
    assert len(aggregated.snapshots) == 2920
    for column in ["objective", "generators", "stores"]:
        assert aggregated.snapshot_weightings[column].sum() == 8760
    energy = aggregated.loads_t.p_set.sum(axis=1) @ aggregated.snapshot_weightings.generators
    assert np.isclose(energy, 16_913_000)
    plants = add_custom_powerplants(
        pd.DataFrame(), ["data/custom/sudan/powerplants_CANDIDATE_ONLY.csv"], "replace"
    )
    assert len(plants) == 11 and plants[["lat", "lon", "Capacity"]].notna().all().all()
    assert plants.projectID.is_unique and (plants.Capacity > 0).all()
    converted = plants.powerplant.convert_country_to_alpha2()
    assert set(converted.Country) == {"SD"}
    out = HERE / "validation"
    out.mkdir(exist_ok=True)
    relevant_keys = [
        "version", "tutorial", "countries", "run", "scenario", "snapshots",
        "enable", "load_options", "atlite", "electricity", "renewable",
        "co2", "costs", "solving",
    ]
    (out / "effective_config.yaml").write_text(
        yaml.safe_dump({k: config[k] for k in relevant_keys}, sort_keys=False)
    )
    run = subprocess.run(
        ["snakemake", "--configfile", "configs/config.sudan-2022.yaml",
         "--cores", "2", "--dry-run", "solve_all_networks"],
        text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    )
    (out / "dry_run.log").write_text(run.stdout)
    cost_file = earth / "resources/sudan-2022-reference/costs_2020.csv"
    report = {
        "status": "passed_input_and_native_interface_checks" if run.returncode == 0 else "dry_run_failed",
        "earth_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "software": {p: importlib.metadata.version(p) for p in ["pypsa", "snakemake", "atlite", "pandas"]},
        "highs": highspy.Highs().version(),
        "input_checks": {
            "native_demand_reader": True, "native_candidate_plant_reader": True,
            "native_country_conversion": True, "native_three_hour_aggregation": True,
            "energy_and_all_duration_weights_preserved": True,
            "tutorial_overrides_removed": True, "projection_database_works": True,
        },
        "demand_GWh": float(energy / 1000),
        "snapshots_after_aggregation": len(aggregated.snapshots),
        "duration_hours": float(aggregated.snapshot_weightings.generators.sum()),
        "candidate_plants": len(plants), "candidate_plants_enabled": False,
        "snakemake_dry_run_exit_code": run.returncode,
        "cds_credential_file_present": (Path.home() / ".cdsapirc").is_file(),
        "cds_environment_pair_present": bool(os.environ.get("CDSAPI_KEY") and os.environ.get("CDSAPI_URL")),
        "era5_cutout_present": (earth / "cutouts/sudan-2022-era5.nc").is_file(),
        "national_solve_performed": False,
        "native_cost_retrieval": {
            "file_present": cost_file.is_file(),
            "sha256": hashlib.sha256(cost_file.read_bytes()).hexdigest() if cost_file.is_file() else None,
            "source": "https://raw.githubusercontent.com/PyPSA/technology-data/v0.13.2/outputs/costs_2020.csv",
            "interpretation": "Generic technology input, not Sudan-calibrated costs",
        },
        "unresolved_scientific_inputs": [
            "2022 reconciled plant fleet and renewable installed capacity",
            "reservoir storage/seasonality and hydro generation reconciliation",
            "882 GWh external supply representation",
            "regional demand allocation and network route/voltage/status validation",
            "common cost currency/year and explicit recovery asset/cost assumptions",
        ],
    }
    (out / "validation.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    if run.returncode:
        print(run.stdout[-6000:])
        raise SystemExit(run.returncode)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--earth", type=Path, required=True)
    main(parser.parse_args().earth)
