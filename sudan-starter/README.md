# PyPSA-Sudan

**A working research starter for Sudan's electricity system.** Built and solved with PyPSA 1.0.6 and HiGHS 1.12.0 in the existing `pypsa` conda environment. Download or clone the repository and open **START_HERE.html** locally for the offline results viewer. GitHub does not render its interactive HTML directly. Example dispatch files and figures are included in `results/`.

**Evidence date: August 2024. Research date: 5 September 2026.** This is a preliminary regional transport model, not a verified reconstruction of September 2026 operations. Demand, corridor capacities, costs and hydro energy are explicit assumptions. Do not present the example dispatch as measured electricity supply or the current national outage rate.

## What is included

- 19 domestic regional buses, including seven isolated regional systems.
- 20 plant records from World Bank Annexes 1–2: 3,647.4 MW nameplate, with separately recorded availability.
- 13 regional transfer corridors: 11 active and two disabled in the baseline. These are PyPSA **Links**, not electrically parameterized AC lines.
- Egypt and Ethiopia imports represented as capped supplies at the relevant domestic regions.
- 168 hourly snapshots, finite hydro energy budgets, and separately reported unserved demand.
- Six solved scenarios, NetCDF networks, CSV dispatch, regional service tables, numerical checks, solver logs, input hashes, interactive HTML, and PNG/SVG figures.
- Downloaded source reports, a historical transmission shapefile, WRI plant data, and an approximate country boundary; data audits preserve conflicts and exclusions.

## Run it

In Anaconda Prompt or PowerShell with conda initialized:

```powershell
conda activate pypsa
cd "$HOME\Desktop\PyPSa-Sudan"
python run_model.py --scenario all
python scripts/make_report.py
python -m pytest -q
```

Or run `./run_all.ps1` in PowerShell. This prepares GIS data, solves all scenarios, creates the report, and runs tests. The existing environment was used without installing or upgrading packages.

For a fast first experiment:

```powershell
python run_model.py --scenario baseline_2024 --hours 24
```

This overwrites that scenario's results and the comparison index. Rerun **all** scenarios with the default 168 hours before regenerating the comparison report.

The Desktop copy includes raw source files for offline use. The public repository omits source PDFs and larger downloaded originals; the example model and results still run without them. Before GIS preparation on a fresh clone, retrieve and verify raw inputs:

```powershell
python scripts/fetch_data.py
python scripts/prepare_data.py
```

`fetch_data.py` checks SHA-256 values against the study manifest. It fails if the upstream source has changed, so a source update requires an explicit new dataset version. A portable environment specification is supplied in `environment.yml`; the exact tested package versions are in `results/run_manifest.json` and `environment-observed.txt`. The portable specification is not a fully locked environment.

## Where to change things

| File | Edit this to change |
|---|---|
| `data/curated/plants.csv` | Plant nameplate, dated available MW, fuel classification, assumed marginal cost |
| `data/curated/buses.csv` | Regional mean demand and approximate bus coordinates |
| `data/curated/corridors.csv` | Assumed transfer capacities and baseline connections |
| `data/curated/imports.csv` | Import availability proxies and assumed prices |
| `config/model.json` | Model horizon, hydro-energy assumption, partial-diesel availability and shortage penalty |
| `config/scenarios.json` | Sensitivity multipliers and restoration switches |
| `src/pypsa_sudan/model.py` | Demand shape, optimization, hydro constraints and result checks |

Do not overwrite a documented observation with an assumption: add its date, source and reason. Existing nameplate and available MW must remain distinct. The `thermal_recovery` case is deliberately hypothetical; it sets thermal availability to 70% of nameplate.

## Inspect a saved network

```python
import pypsa
n = pypsa.Network("results/baseline_2024/network.nc")
print(n.generators[["bus", "carrier", "p_nom", "p_max_pu"]])
print(n.generators_t.p.head())
print(n.meta)
```

Generators with carrier `unserved` are shortage variables. Never count them as power plants or physical generation. Carriers `import` are external supply proxies, not Sudanese installed generation.

## Public repository

The runnable starter is published at https://github.com/Elgenied/pypsa-sudan/tree/main/sudan-starter inside the existing PyPSA-Earth fork. The Desktop folder remains the standalone working model. The upstream workflow and this starter are separate entry points.

See [the CCG Sudan dataset assessment](docs/CCG_STARTER_KIT_REVIEW.md) for the reference tables supplied by the Research Square paper. They have been archived without changing the solved baseline.

## Research documentation

- [Data sources and what to fetch next](docs/DATA_SOURCES.md)
- [Methodology, units and limitations](docs/METHODOLOGY.md)
- [A realistic publication roadmap](docs/PUBLICATION_ROADMAP.md)
- [PyPSA community and PyPSA-Earth integration](docs/COMMUNITY.md)
- [Third-party data rights](docs/DATA_LICENSES.md)
- [Template for requesting utility data](docs/DATA_REQUEST_TEMPLATE.md)

Original code is offered under MIT; third-party data retain their own licenses. This is an independent project using PyPSA, without implied endorsement or official PyPSA affiliation.
