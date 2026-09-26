# PyPSA-Sudan

**Research direction: least-cost electricity recovery and expansion of access in Sudan.**

The question is: **Where should Sudan rehabilitate or extend the grid, where should it build mini-grids, and where are standalone systems more economical—at a specified level of service?**

**Current stage:** a nationally calibrated 2022 dispatch prototype and a historical evidence collection. A settlement-level electrification optimizer and recommendation map have **not yet been built**.

## Start here

| Read in this order | What it tells you |
|---|---|
| **1. [Overall study plan](docs/STUDY_PLAN.md)** | Research question, grid / mini-grid / standalone comparison, PyPSA's role and milestones |
| **2. [Evidence, validation and gaps](docs/EVIDENCE_AND_GAPS.md)** | What we have, what was checked, what is assumed and what is missing |
| **3. [2022 system notebook](Sudan_2022.ipynb)** | Running dispatch model, national calibration, regional maps and stress tests |
| **4. [Historical evidence notebook](research/forecasting_2012/Sudan_Forecasting_Replication.ipynb)** | Recovered 2012-report data, replicated calculations, regional sector pies and source conflicts |

There are **two notebooks with different jobs**. Each begins with a reader guide and ends with its role in the next study. Saved results can be viewed on GitHub without running Python. The [2022 HTML](Sudan_2022.html) and [historical HTML](research/forecasting_2012/Sudan_Forecasting_Replication.html) are downloadable browser reading copies of those same notebooks.

## What exists today

| Workstream | Available | Validation status | What it can answer |
|---|---|---|---|
| **2022 system reference** | 19 regional nodes, 13 schematic corridors, 8,760 hours; fixed-capacity dispatch | Numerical feasibility checked; national annual totals calibrated; regional/hourly operation not independently validated | How dispatch changes under the stated hydro/corridor assumptions |
| **Historical evidence** | 20 cataloged datasets; 19 plant/configuration records; 131 historical localities; consumption, hydro, heat rates and forecasts | Ten arithmetic checks passed; source inconsistencies retained | What the report contains, how its visible calculations work and which inputs could improve the baseline |
| **Post-war electrification planning** | Research design and prioritized gaps | **Planned; not implemented** | Intended: which service option, where, when, capacity and cost |

**Calibration is not independent validation.** Matching inputs does not confirm the network or operation. The 2012 report's forecasts for 2022 are not observations. Its locality table is not a settlement GIS dataset.

## Find the right files

```text
README.md                         Project map and reading order
docs/
  STUDY_PLAN.md                   Research design, PyPSA role and milestones
  EVIDENCE_AND_GAPS.md            Evidence status, checks and missing inputs
Sudan_2022.ipynb                  Main 2022 model; inputs embedded here
Sudan_2022.html                   Reading copy of the same notebook
results/                         Generated model outputs, not new observations
data/
  README.md                      Dataset navigation and update instructions
  catalog.json                   Index/checksums; does not duplicate CSVs
research/forecasting_2012/
  Sudan_Forecasting_Replication.ipynb   Historical analysis notebook
  data/                          Canonical extracted historical CSVs
  results/                       Recalculated outputs and source issues
  SOURCE_REGISTER.md             Original data owners and links
  DATA_DICTIONARY.md             Units, definitions and extraction rules
scripts/                         Catalog maintenance
.github/workflows/               Automated execution and integrity checks
```

Use the [data collection](data/README.md) for input evidence. Use [2022 results](results/) or [historical results](research/forecasting_2012/results/) for calculated outputs. **Historical CSVs are not yet integrated into the 2022 model.** The evidence register identifies the remaining reconciliation work.

## Next milestone

Prepare a **small settlement-level comparison of grid connection, mini-grid and standalone supply**, with matched service requirements and documented costs. In parallel, reconcile the 2022 fleet and introduce evidence-based hydro seasonality. The pilot must explain its costs and expose missing inputs before producing a national recommendation map. See the [milestones and completion criteria](docs/STUDY_PLAN.md#milestones-and-completion-criteria).

## Run

With the existing environment:

```shell
conda activate pypsa
python -m ipykernel install --user --name pypsa --display-name "Python (pypsa)"
jupyter lab Sudan_2022.ipynb
```

Select **Python (pypsa)** and **Run All**. Batch commands from the repository root:

```shell
# Baseline plus two full-year stress tests; allow a few minutes
python run_notebook.py --kernel pypsa

# Historical replication: included CSVs; no PDF or internet needed
python research/forecasting_2012/run_notebook.py --kernel pypsa

# Historical data integrity
python scripts/data_catalog.py --check
```

For a new environment, use Python 3.13 and install `requirements.txt`; extracting a local PDF also needs the historical package's requirements. Add `--export-only` to either runner to refresh its HTML after a markdown-only notebook edit. See [dataset maintenance](data/README.md) for data updates.

## Sources and project history

The baseline uses UNSD and World Bank sources cited in its notebook. Historical inputs have a [source register](research/forecasting_2012/SOURCE_REGISTER.md) and [rights/qualification notes](research/forecasting_2012/DATA_SOURCES_AND_RIGHTS.md). Original project code is MIT licensed; third-party material is not relicensed. The original PDF and raw page exports remain outside the public repository.

Earlier exploratory files are preserved in Git history at `legacy-before-single-notebook-20260914`. Active work is the two notebooks above. PyPSA-Sudan is an independent research project, without implied PyPSA endorsement. A paper release still needs claim-appropriate validation, uncertainty analysis and an archived reproducible version.
