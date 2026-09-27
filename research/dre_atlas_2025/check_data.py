"""Check committed spatial inputs against the reviewed source transformation."""

import json
from pathlib import Path

import geopandas as gpd
import pandas as pd

from prepare_data import assess, digest

DATA = Path(__file__).resolve().parent / "data"
expected = json.loads((DATA / "validation_report.json").read_text(encoding="utf-8"))
for name, sha in expected["derived_sha256"].items():
    assert digest(DATA / name) == sha, f"Changed dataset: {name}"
attrs = pd.read_csv(DATA / "settlement_attributes.csv.gz")
boundaries = gpd.read_parquet(DATA / "settlement_boundaries_100m.parquet")
actual = assess(attrs, boundaries)
for key, value in actual.items():
    assert expected[key] == value, f"Changed validation result: {key}"
print(f"Verified {len(attrs):,} settlement records, source arithmetic, GIS and dataset checksums")
