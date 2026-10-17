# PyPSA-Sudan data collection

[Project start page](../README.md) · [Evidence and missing inputs](../docs/EVIDENCE_AND_GAPS.md) · [Overall study plan](../docs/STUDY_PLAN.md)

This directory indexes three evidence collections. [catalog.json](catalog.json) covers 20 historical CSVs, with paths, row counts, columns, sources, SHA256 checksums and vintages. The [DRE spatial collection](../research/dre_atlas_2025/README.md) has its own [source and derived checksum register](../research/dre_atlas_2025/data/validation_report.json). The [report evidence collection](report_evidence/README.md) adds dated prices, fleet status, demand, policy targets and published study assumptions from the October 2026 PDF review. Historical and DRE files stay with their notebooks; the new tables live here under `report_evidence/`.

Checksums normalize CRLF to LF, matching Git's text normalization, so the same data verify on Windows and Linux.

## Historical collection

**Sudan forecasting report, 2012:** 19 plant/configuration records, 131 localities, state-sector consumption from 2006–2011, historical demographics and GDP, hydro and heat-rate curves, transmission information, and three sets of forecasts for 2012–2031. There are also source metadata and a separately attributed 2019 implementation cross-check.

- [Executed research notebook](../research/forecasting_2012/Sudan_Forecasting_Replication.ipynb)
- [Data dictionary](../research/forecasting_2012/DATA_DICTIONARY.md)
- [Source register](../research/forecasting_2012/SOURCE_REGISTER.md)
- [Known source issues](../research/forecasting_2012/results/source_issues.csv)
- [Source and rights notes](../research/forecasting_2012/DATA_SOURCES_AND_RIGHTS.md)

The root `Sudan_2022.ipynb` remains the main dispatch model. Its input tables and national calibration remain unchanged by the addition of this collection. Historical data should be matched and validated before replacing baseline assumptions.

## Spatial settlement collection

The [DRE Atlas notebook](../research/dre_atlas_2025/Sudan_DRE_Settlements.ipynb) uses 33,891 georeferenced clusters, complete non-geometry source attributes and simplified display polygons. The raw full-resolution data remain at the [World Bank catalog](https://energydata.info/dataset/sudan-distributed-renewable-energy-dre). Demand is a low-service building formula, not measured electricity or a uniform 2022 snapshot. Historical conflict labels use 2020–2022.

The grid / mini-grid / standalone **cost accounting** in [system_costs](system_costs/README.md) is now used by an [hourly three-cluster pilot](electrification_pilot/README.md). Section 7 of the [same notebook](../research/system_costs/Sudan_System_Costs.ipynb) optimizes local capacities and dispatch, with explicit proxy routes and assumed service targets. It does not implement joint national route planning or field-validated option selection. The 131 historical localities and 33,891 DRE clusters are different spatial units; there is no validated crosswalk or post-war access inventory.

The [uncertainty experiment](electrification_uncertainty/README.md) supplies section 8 of that notebook: editable test ranges and joint scenarios for re-optimized comparisons, route and demand thresholds, and data priorities. These inputs are analyst assumptions, not additional observations or probability distributions.

The [spatial proxy-demand study](spatial_proxy_study/README.md) supplies section 9: 18 selected source clusters (one per state), building-based daily demand, two recovery-service targets and cached hourly weather at each location. It proceeds using available inputs, with explicit grid-assessment coverage and no national extrapolation. It adds a sample analysis, not measured customer demand.

## Maintain or update historical data

1. Change the extraction script or source data with an explicit source/page reference. Preserve missing values and distinguish observations, assumptions and forecasts.
2. If re-extracting, provide the original PDF locally to `research/forecasting_2012/extract_data.py`. Do not commit the PDF or raw page exports; these are excluded from this public collection. The extraction cache is document-specific.
3. From the repository root, run:

   ```shell
   python research/forecasting_2012/build_notebook.py
   python research/forecasting_2012/run_notebook.py
   python scripts/data_catalog.py
   python scripts/data_catalog.py --check
   ```

4. Review the executed notebook, figures, validation results, source-issue register and catalog diff before committing. Update the dictionary and source metadata when definitions or sources change.

The `Check historical data and replication` workflow verifies file integrity and reruns the notebook on relevant changes. These checks detect catalog drift and calculation regressions; they do not prove the source's historical accuracy or automatically fetch new data. New evidence requires a reviewed update.

For a DRE update, follow [the spatial collection's rebuild instructions](../research/dre_atlas_2025/README.md), review changes to original checksums and source definitions, then rerun the spatial notebook. Its workflow checks committed data and notebook output without downloading the original large files.
