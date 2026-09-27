# Sudan DRE settlement atlas (June 2025 release)

[Project guide](../../README.md) · [Executed notebook](Sudan_DRE_Settlements.ipynb) · [HTML reading copy](Sudan_DRE_Settlements.html) · [Source register](SOURCE_REGISTER.md)

This collection has **33,891 Sudan settlement clusters** with the 41 original non-geometry CSV columns. `geohash` joins to 33,891 simplified display polygons in EPSG:4326. The source MultiPolygons are simplified at **100 m in EPSG:6933** for mapping; use the source GeoJSON for route measurement or detailed boundary analysis. The raw CSV and GeoJSON are 135 and 229 MB and remain at the [public catalog](https://energydata.info/dataset/sudan-distributed-renewable-energy-dre). The committed attributes and display boundaries are about 5.2 MB together.

| File | Meaning |
|---|---|
| `data/settlement_attributes.csv.gz` | Full source attributes, except the duplicate polygon WKT; gzip CSV read by pandas |
| `data/settlement_boundaries_100m.parquet` | Simplified display geometry keyed by `geohash`; GeoParquet |
| `data/attribute_dictionary.csv` | The source dictionary's 56-row Overview sheet, including fields absent in Sudan |
| `data/validation_report.json` | Original/derived SHA256 hashes, totals, checks and retained source anomalies |
| `prepare_data.py` | Rebuild the three committed files from the original public downloads |
| `check_data.py` | Verify committed hashes, joins, arithmetic and geometry without downloading |

The notebook has source definitions, national and state visuals, grid-distance screens, a historical conflict-exposure chart, arithmetic validation, and a model-input schema. **It does not choose grid, mini-grid or standalone technology.** The atlas estimated 17,589,336 potential building connections and 6,276,952.8 kWh/day low-service demand, neither of which is measured access or metered electricity. Historical security labels use **2020–2022** fatalities; light-at-night uses **September 2022–August 2023**. See [the methods and provenance](SOURCE_REGISTER.md) before reusing either as a scenario input.

From repository root, with the `pypsa` conda environment:

```shell
python research/dre_atlas_2025/check_data.py
python research/dre_atlas_2025/run_notebook.py --kernel pypsa
```

To rebuild after downloading the three original resources from the catalog:

```shell
python research/dre_atlas_2025/prepare_data.py --csv path/to/sudan_dre_atlas_settlements.csv --geojson path/to/sudan_dre_atlas_settlements.geojson --dictionary path/to/settlement_data_overview.xlsx
```

The script refuses a source with changed checksums until the new release is reviewed. `--allow-new-source` is for an intentionally updated release; revise this register, inspect differences, rerun the notebook and check the outputs before committing.
