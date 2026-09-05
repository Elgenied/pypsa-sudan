"""Build auditable country subsets and plant/location reconciliation; run offline."""
from pathlib import Path
import json
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/raw"
OUT = ROOT / "data/processed"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    countries = gpd.read_file(RAW / "natural_earth_countries.geojson")
    sudan = countries[countries["ADM0_A3"] == "SDN"].to_crs(4326)
    assert len(sudan) == 1
    sudan.to_file(OUT / "sudan_boundary.geojson", driver="GeoJSON")
    boundary = sudan.geometry.union_all()
    wri = pd.read_csv(RAW / "gppd_global.csv", low_memory=False)
    wri = wri[wri.country == "SDN"].copy()
    wri["inside_approximate_modern_boundary"] = [boundary.covers(Point(x, y)) for x, y in zip(wri.longitude, wri.latitude)]
    wri["review_action"] = wri.inside_approximate_modern_boundary.map({True: "historical candidate; never automatically added", False: "manual review required; outside coarse boundary alone does not establish country"})
    wri.loc[wri.name.isin(["Kuku", "Melut Sugar Factory"]), "review_action"] = "excluded: historical SDN code but located in present-day South Sudan"
    wri.loc[wri.name == "Port Sudan", "review_action"] = "coastal-resolution flag; retain for review; not identified as the Turkish barge"
    wri.to_csv(OUT / "wri_sudan_candidates_audit.csv", index=False)
    # Stable source feature IDs are positions in the downloaded shapefile.
    grid = gpd.read_file(RAW / "wb_transmission.zip").to_crs(4326)
    grid["source_feature_id"] = [f"WB_AICD_{i:03d}" for i in range(len(grid))]
    grid["used_as_electrical_line"] = False
    grid["review_action"] = grid.STATUS.map({"Existing": "historical geometry only; operating state and rating unverified", "Planned": "historically planned; requires later commissioning evidence", "Missing": "excluded hypothetical project", "Under Study": "excluded study project"})
    grid.drop(columns="geometry").to_csv(OUT / "transmission_feature_audit.csv", index=False)
    grid.geometry = grid.geometry.intersection(boundary)
    grid = grid[~grid.geometry.is_empty].copy()
    grid.to_file(OUT / "historical_transmission_clipped.geojson", driver="GeoJSON")
    # Coordinates in buses.csv are deliberately approximate regional display points.
    buses = pd.read_csv(ROOT / "data/curated/buses.csv").set_index("bus")
    plants = pd.read_csv(ROOT / "data/curated/plants.csv", keep_default_na=False)
    lookup = wri.set_index("gppd_idnr")
    for i, plant in plants.iterrows():
        ref = plant.wri_location_id
        if ref:
            row = lookup.loc[ref]
            if not row.inside_approximate_modern_boundary:
                raise ValueError(f"Plant {plant.plant_id} matches outside Sudan")
            plants.loc[i, "longitude"] = row.longitude
            plants.loc[i, "latitude"] = row.latitude
            plants.loc[i, "coordinate_quality"] = "historical WRI location match; unverified plant footprint"
            plants.loc[i, "wri_capacity_mw_reference_only"] = row.capacity_mw
        else:
            plants.loc[i, "longitude"] = buses.loc[plant.bus, "longitude"]
            plants.loc[i, "latitude"] = buses.loc[plant.bus, "latitude"]
            plants.loc[i, "coordinate_quality"] = "regional bus proxy; NOT a known plant location"
    plants.to_csv(OUT / "plants_geolocated.csv", index=False)
    gpd.GeoDataFrame(plants, geometry=gpd.points_from_xy(plants.longitude, plants.latitude), crs=4326).to_file(OUT / "plants.geojson", driver="GeoJSON")
    audit = {"wri_sdn_rows": len(wri), "wri_outside_boundary": int((~wri.inside_approximate_modern_boundary).sum()), "historical_grid_features_original": 30, "historical_features_intersecting_sudan": len(grid), "curated_plant_records": len(plants), "installed_capacity_mw": float(plants.p_nom_mw.sum()), "location_proxy_count": int((plants.wri_location_id == "").sum()), "boundary_caveat": "Natural Earth 1:110m is a coarse reference, not a legal or detailed border determination."}
    (OUT / "data_audit.json").write_text(json.dumps(audit, indent=2))
    print(json.dumps(audit, indent=2))


if __name__ == "__main__":
    main()
