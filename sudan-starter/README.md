# PyPSA-Sudan

**Historical reference year: 2022.** The default model is a solved, full-year national electricity dispatch benchmark based on UNSD annual statistics. The selected year, source flags, accounting and limitations are explained in [the reference-year note](docs/REFERENCE_YEAR_2022.md).

2022 is the latest year in the current UNSD Electricity Profiles edition with Sudan's headline and major generation categories not flagged as UN estimates. Consumption and Other capacity still have estimate flags. This is a defensible statistical starting point, not a complete or validated plant-level reconstruction.

## Run the reference model

From this folder, with the supplied environment or the existing `pypsa` conda environment:

```shell
conda activate pypsa
python run_model.py
python scripts/make_reference_report.py
python -m pytest -q
```

On the original computer, this standalone folder is `Desktop/PyPSa-Sudan`. In a clone of the public repository, first run `cd sudan-starter`. `run_all.ps1` now solves the 2022 benchmark, builds its report and runs tests. GIS downloads are not needed for this aggregate benchmark.

Open **START_HERE.html** locally for the results viewer; GitHub does not render interactive/local HTML as a webpage. Example results are included in `results/reference_2022/`, so they can be inspected without solving again.

## What the 2022 model represents

- 8,760 consecutive hourly snapshots and one national bus, with unrestricted internal transfers.
- 4,209 MW of net installed capacity: 2,134 MW combustible fuels, 1,885 MW hydro, 190 MW Other. These are national aggregates, not three physical plants.
- Net domestic generation of 16.031 TWh and imports of 0.882 TWh, balanced against 13.261 TWh consumption plus 3.652 TWh system losses.
- Synthetic hourly load, an annual hydro budget, fixed average imports, flat Other output and assumed merit-order costs. Hydro timing, outages, interconnector ratings and regional bottlenecks are not established by these statistics.
- Explicit reconciliation of gross and net output, a 1 GWh category-rounding difference, source estimate flags, missing exports and national/autoproducer coverage.

Annual agreement is calibration, not independent empirical validation. Demand represents supplied consumption, not latent demand. Zero model shortage does not mean Sudan had no outages in 2022. Costs and monthly dispatch are illustrative.

## Code, data and outputs

| File | Purpose |
|---|---|
| `src/pypsa_sudan/reference.py` | Default 2022 annual dispatch, accounting and numerical checks |
| `config/reference_2022.json` | Year, cost assumptions and sensitivity multipliers |
| `data/reference/unsd_2022/statistics.csv` | Source statistics with units, coverage and flags |
| `data/reference/unsd_2022/source_manifest.json` | Source URL, page, retrieval date and PDF hash |
| `results/reference_2022/network.nc` | Solved PyPSA network |
| `results/reference_2022/dispatch_mw.csv` | Hourly model dispatch |
| `results/reference_2022/calibration_comparison.csv` | Derived net targets versus model output |
| `results/reference_2022/validation.json` | Numerical checks, not independent validation |
| `notebooks/02_reference_2022.ipynb` | Explore the historical benchmark |

```python
import pypsa
n = pypsa.Network("results/reference_2022/network.nc")
print(n.meta)
print(n.generators_t.p.sum() / 1000)  # GWh; one-hour weights
```

Imports and `unserved` are not domestic generation capacity. Scenario edits overwrite the reference results; preserve a baseline before sensitivity analysis. The tested package versions and input hashes are in the reference result folder; `environment.yml` specifies a portable environment, not a full lockfile.

## Earlier regional illustration

The **19-region, 20-plant, six-scenario model is a separate legacy 2024 illustration**. It retains dated wartime status and assumed regional demand and corridor ratings. It has not been converted into a 2022 network by changing its label. Its plant/GIS audit is useful starting material for a year-specific reconstruction.

```shell
python run_model.py --scenario all
python scripts/make_report.py
```

These explicit commands solve the legacy scenarios and write **LEGACY_2024.html**. Legacy configuration is in `config/model.json` and `config/scenarios.json`, with inputs in `data/curated/` and code in `src/pypsa_sudan/model.py`. The original notebook `01_explore_sudan.ipynb` is also legacy 2024. Legacy `--hours` overrides are supported; the 2022 benchmark always uses the complete year.

To refresh the historical GIS audit on a fresh clone, run `python scripts/fetch_data.py` then `python scripts/prepare_data.py`. The fetcher verifies raw input hashes and rejects changed upstream files. Source PDFs and larger originals are omitted from Git; the local Desktop copy retains the original research material.

## Toward a publishable regional model

The next priorities are a dated 2022 unit ledger, net/gross capacity reconciliation, substation and line topology/ratings, monthly demand and hydro, import flows, outages and consistent 2022 costs. Obtain independent observations for validation and quantify remaining uncertainty. A national accounting benchmark alone is not the proposed spatial research contribution.

- [Reference-year decision and missing data](docs/REFERENCE_YEAR_2022.md)
- [Publication roadmap](docs/PUBLICATION_ROADMAP.md)
- [Data sources](docs/DATA_SOURCES.md)
- [Assessment of the CCG Sudan paper and archived reference tables](docs/CCG_STARTER_KIT_REVIEW.md)
- [Community and PyPSA-Earth integration](docs/COMMUNITY.md)
- [Data request template](docs/DATA_REQUEST_TEMPLATE.md)
- [Third-party data rights](docs/DATA_LICENSES.md)

Public code: https://github.com/Elgenied/pypsa-sudan/tree/main/sudan-starter. This starter and the upstream PyPSA-Earth workflow are separate entry points. Original starter code is MIT licensed; upstream code and third-party data retain their own licenses. This independent project has no implied official PyPSA endorsement.
