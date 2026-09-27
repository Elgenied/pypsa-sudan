"""Rebuild the committed Sudan DRE tables from the public 2025 downloads.

Usage: python research/dre_atlas_2025/prepare_data.py --csv PATH --geojson PATH --dictionary PATH
The original 135/229 MB downloads are kept outside Git; see SOURCE_REGISTER.md.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import shapely

HERE = Path(__file__).resolve().parent
EXPECTED_SOURCE_SHA256 = {
    "csv": "63c23d9920cc7faebc800fda2256ac857b2971fd10c321b66c810595853723e3",
    "geojson": "d49923f7091db61dd41f6995afa615fc87d67c848139128701dc3bfe988ffcc9",
    "dictionary": "fd49f1e0d2ace31b7e5dda27a648f1f1f15a187da04c7539646a44064b219905",
}


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def assess(attributes: pd.DataFrame, boundaries: gpd.GeoDataFrame) -> dict:
    """Check joins, published arithmetic and geometry; retain source discrepancies."""
    assert len(attributes) == len(boundaries) == 33891
    assert attributes.geohash.is_unique and boundaries.geohash.is_unique
    assert set(attributes.geohash) == set(boundaries.geohash)
    assert boundaries.crs.to_epsg() == 4326
    assert boundaries.geometry.is_valid.all() and not boundaries.geometry.is_empty.any()
    assert attributes.lat.between(9, 24).all() and attributes.lon.between(21, 39).all()
    assert attributes.num_connections.eq(attributes.num_buildings).all()
    assert attributes.num_buildings.eq(
        attributes.large_buildings + attributes.medium_buildings + attributes.small_buildings
    ).all()

    expected_demand = (
        1.1 * attributes.large_buildings
        + 0.65 * attributes.medium_buildings
        + 0.335 * attributes.small_buildings
    )
    demand_error = (expected_demand - attributes.demand).abs()
    assert demand_error.max() <= 0.050001  # one-decimal source rounding
    assert (expected_demand / attributes.num_connections - attributes.demand_connection).abs().max() <= 0.000501

    fatality_counts = {}
    for radius in (25, 50):
        parts = attributes[f"fatalities_within_{radius}km"].str.split(";", expand=True)
        assert parts.shape[1] == 4
        fatality_counts[radius] = parts.astype(int).sum(axis=1)
    expected_risk = np.select(
        [fatality_counts[25] > 0, fatality_counts[50] > 0],
        ["high", "medium"],
        default="low",
    )
    assert (expected_risk == attributes.security_risk).all()

    report = {
        "settlements": len(attributes),
        "unique_ids": int(attributes.geohash.nunique()),
        "attributes_per_settlement_including_id": len(attributes.columns),
        "geometry_type": boundaries.geometry.geom_type.value_counts().to_dict(),
        "connections_estimated_potential": int(attributes.num_connections.sum()),
        "population_modelled": int(attributes.population.sum()),
        "demand_kwh_per_day_source_rounded_sum": round(float(attributes.demand.sum()), 1),
        "demand_kwh_per_day_formula_sum": round(float(expected_demand.sum()), 1),
        "max_settlement_demand_rounding_error_kwh_day": round(float(demand_error.max()), 4),
        "risk_class_counts_2020_2022": attributes.security_risk.value_counts().to_dict(),
        "nightlight_source_flag_vs_overlap_disagreements": int(
            ((attributes.overlap_percentage > 0) != attributes.has_nightlight).sum()
        ),
        "road_flag_vs_rounded_half_km_disagreements": int(
            ((attributes.dist_main_road_km <= 0.5) != attributes.main_road_access).sum()
        ),
        "density_above_100_percent_records": int((attributes.building_density_percent > 100).sum()),
        "wealth_index_nonmissing": int(attributes.mean_rwi.notna().sum()),
        "admin_1_missing": int(attributes.admin_cgaz_1.isna().sum()),
    }
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path, required=True)
    parser.add_argument("--geojson", type=Path, required=True)
    parser.add_argument("--dictionary", type=Path, required=True)
    parser.add_argument("--allow-new-source", action="store_true", help="Review and record an updated source separately")
    args = parser.parse_args()
    paths = {"csv": args.csv, "geojson": args.geojson, "dictionary": args.dictionary}
    source_hashes = {key: digest(value) for key, value in paths.items()}
    if not args.allow_new_source and source_hashes != EXPECTED_SOURCE_SHA256:
        raise ValueError("Source checksum differs from reviewed release; inspect the source before updating data")

    raw = pd.read_csv(args.csv)
    geo = gpd.read_file(args.geojson)
    assert raw.geohash.is_unique and geo.geohash.is_unique
    assert set(raw.geohash) == set(geo.geohash)
    assert set(raw.columns) == set(geo.columns)
    # Check every non-geometry value is the same in the two published files.
    for key in raw.columns.drop("geometry"):
        left = raw.set_index("geohash")[key] if key != "geohash" else None
        right = geo.set_index("geohash")[key] if key != "geohash" else None
        if key != "geohash" and not left.sort_index().equals(right.sort_index()):
            # The CSV and GeoJSON use different numeric parsers; compare values with a tiny tolerance.
            a, b = left.sort_index(), right.sort_index()
            if pd.api.types.is_numeric_dtype(a) and pd.api.types.is_numeric_dtype(b):
                assert np.allclose(a, b, atol=1e-8, rtol=0, equal_nan=True), key
            else:
                assert a.fillna("").astype(str).equals(b.fillna("").astype(str)), key
    # CSV WKT is rounded to six decimal places; GeoJSON retains finer coordinates.
    csv_geom = shapely.from_wkt(raw.sort_values("geohash").geometry.to_numpy())
    geo_geom = geo.sort_values("geohash").geometry.to_numpy()
    polygon_match = shapely.equals_exact(csv_geom, geo_geom, 1e-6)
    assert polygon_match.all()

    attrs = raw.drop(columns="geometry").sort_values("geohash").reset_index(drop=True)
    boundaries = geo[["geohash", "geometry"]].sort_values("geohash").reset_index(drop=True)
    assess(attrs, boundaries)  # Validate full-resolution source before simplifying.
    # Boundaries are for a readable map; fetch the original polygon file for route analysis.
    simplified = boundaries.to_crs(6933)
    simplified.geometry = simplified.geometry.simplify(100, preserve_topology=True)
    simplified = simplified.to_crs(4326)
    assert simplified.geometry.is_valid.all()
    report = assess(attrs, simplified)
    report["source_geometry_type"] = boundaries.geometry.geom_type.value_counts().to_dict()
    report["source_csv_geojson_polygons_match_within_1e_6_degrees"] = int(polygon_match.sum())

    out = HERE / "data"
    out.mkdir(exist_ok=True)
    attrs.to_csv(out / "settlement_attributes.csv.gz", index=False, compression={"method": "gzip", "mtime": 0})
    simplified.to_parquet(out / "settlement_boundaries_100m.parquet", index=False, compression="zstd")
    dictionary = pd.read_excel(args.dictionary, sheet_name="Overview")
    for column in dictionary.select_dtypes(include="object"):
        dictionary[column] = dictionary[column].str.strip()
    dictionary.to_csv(out / "attribute_dictionary.csv", index=False, lineterminator="\n")
    report["source_sha256"] = source_hashes
    report["derived_sha256"] = {p.name: digest(p) for p in sorted(out.iterdir()) if p.is_file() and p.name != "validation_report.json"}
    (out / "validation_report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
