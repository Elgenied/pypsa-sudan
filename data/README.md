# PyPSA-Sudan data collection

[Project start page](../README.md) · [Evidence and missing inputs](../docs/EVIDENCE_AND_GAPS.md) · [Overall study plan](../docs/STUDY_PLAN.md)

This is a versioned collection of CSV datasets, indexed by [catalog.json](catalog.json). Each entry records its path, row count, columns, source, SHA256 checksum and vintage. The canonical CSVs are under [`research/forecasting_2012/data/`](../research/forecasting_2012/data/); they are not duplicated here.

Checksums normalize CRLF to LF, matching Git's text normalization, so the same data verify on Windows and Linux.

## Available collection

**Sudan forecasting report, 2012:** 19 plant/configuration records, 131 localities, state-sector consumption from 2006–2011, historical demographics and GDP, hydro and heat-rate curves, transmission information, and three sets of forecasts for 2012–2031. There are also source metadata and a separately attributed 2019 implementation cross-check.

- [Executed research notebook](../research/forecasting_2012/Sudan_Forecasting_Replication.ipynb)
- [Data dictionary](../research/forecasting_2012/DATA_DICTIONARY.md)
- [Source register](../research/forecasting_2012/SOURCE_REGISTER.md)
- [Known source issues](../research/forecasting_2012/results/source_issues.csv)
- [Source and rights notes](../research/forecasting_2012/DATA_SOURCES_AND_RIGHTS.md)

The root `Sudan_2022.ipynb` remains the main dispatch model. Its input tables and national calibration remain unchanged by the addition of this collection. Historical data should be matched and validated before replacing baseline assumptions.

The study's planned settlement-level grid / mini-grid / standalone comparison is not implemented in either notebook yet. In particular, the 131 historical localities do not provide a georeferenced settlement map or validated post-war access inventory.

## Maintain or update the collection

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
