# PyPSA-Sudan

**Research direction: least-cost electricity recovery and expansion of access in Sudan.**

The question is: **Where should Sudan rehabilitate or extend the grid, where should it build mini-grids, and where are standalone systems more economical—at a specified level of service?**

**Start with section 11 of the [electrification notebook](research/system_costs/Sudan_System_Costs.ipynb): national supply coupling.** Eight neighbouring Blue Nile clusters (978 potential connections) are linked to the 19-node national dispatch model under three local recovery conditions. Shared routes, repairs, hourly service and additional national supply costs are optimized with checked upper/lower cost bounds. This is a nationally supplied regional access plan, not yet a country-wide allocation. [Formulation, evidence and reproduction](docs/NATIONAL_COUPLING.md). Section 10 retains the earlier four-cluster demonstration.

The repository also retains the nationally calibrated 2022 dispatch prototype, historical/report evidence, settlement atlas, complete cost ledger, three-cluster pilot, uncertainty/break-even analysis and 18-state sample. Measured settlement demand is not a prerequisite for conditional planning. Multi-region access allocation, national asset investment, sequencing and field-validated recommendations remain future work.

## Start here

| Read in this order | What it tells you |
|---|---|
| **1. [Overall study plan](docs/STUDY_PLAN.md)** | Research question, grid / mini-grid / standalone comparison, PyPSA's role and milestones |
| **2. [Evidence, validation and gaps](docs/EVIDENCE_AND_GAPS.md)** | What we have, what was checked, what is assumed and what is missing |
| **3. [2022 system notebook](Sudan_2022.ipynb)** | Running dispatch model, national calibration, regional maps and stress tests |
| **4. [Historical evidence notebook](research/forecasting_2012/Sudan_Forecasting_Replication.ipynb)** | Recovered 2012-report data, replicated calculations, regional sector pies and source conflicts |
| **5. [Settlement atlas notebook](research/dre_atlas_2025/Sudan_DRE_Settlements.ipynb)** | Settlement maps, source formula checks, state summaries, grid-distance screens and spatial gaps |
| **6. [Report evidence and usage guide](data/report_evidence/README.md)** | October 2026 review: dated equipment/fuel prices, plant status, sector sales, published assumptions, source conflicts and modelling uses |
| **7. [System-cost and electrification notebook](research/system_costs/Sudan_System_Costs.ipynb)** | **Read section 11 first: eight-cluster plans coupled to national dispatch, maps, connection shares, costs and bounds.** Sections 1–10 retain accounting and supporting studies. |

There are **four notebooks with different jobs**. Each begins with a reader guide and ends with its role in the next study. Saved results can be viewed on GitHub without running Python. The [2022 HTML](Sudan_2022.html), [historical HTML](research/forecasting_2012/Sudan_Forecasting_Replication.html), [settlement HTML](research/dre_atlas_2025/Sudan_DRE_Settlements.html) and [cost HTML](research/system_costs/Sudan_System_Costs.html) are browser reading copies of those notebooks.

## What exists today

| Workstream | Available | Validation status | What it can answer |
|---|---|---|---|
| **2022 system reference** | 19 regional nodes, 13 schematic corridors, 8,760 hours; fixed-capacity dispatch | Numerical feasibility checked; national annual totals calibrated; regional/hourly operation not independently validated | How dispatch changes under the stated hydro/corridor assumptions |
| **Historical evidence** | 20 cataloged datasets; 19 plant/configuration records; 131 historical localities; consumption, hydro, heat rates and forecasts | Ten arithmetic checks passed; source inconsistencies retained | What the report contains, how its visible calculations work and which inputs could improve the baseline |
| **Settlement atlas** | 33,891 clusters; 41 source attribute columns and display polygons | Source CSV/GeoJSON IDs and values match; demand and 2020–2022 risk rules reproduce; anomalies logged | Where mapped clusters and screening indicators are; no technology choice |
| **Report evidence** | 23 evidence tables from 19 supplied PDF files (18 distinct documents); source, issue and data-lead registers | Source/page attribution, hashes, schema checks and 23 arithmetic comparisons; two arithmetic discrepancies retained | Historical cross-checks and dated recovery/cost scenario evidence; not approved model inputs |
| **System costs** | 17 component costs, 24 parameters, four fixed 100-home designs, three cost/finance cases; one cost notebook | Accounting and limiting-case tests pass; prices are provisional analyst assumptions and adequacy is untested | Traceable full-scope budgets and sensitivities; no feasible least-cost winner or country total |
| **Electrification pilot** | Three real DRE clusters; complete 2022 NASA POWER weather; 18 full-year PyPSA sizing/dispatch cases in the cost notebook | Hourly balance, SOC, operating limits, service equality and lifecycle-objective reconciliation checked; no field validation | Conditional local sizing and option rankings; tests grid interruption, unavailable diesel and higher demand |
| **Uncertainty and break-even** | Ten single-input sensitivities; eight joint scenarios per cluster; refined demand crossings and exact fixed-loss MV route thresholds | Saved hourly outputs and lifecycle costs independently reconstructed; scenario counts are not probabilities | Which assumptions can overturn local rankings; where to target evidence collection; no fixed-design robustness or national optimum |
| **Spatial proxy-demand study** | 18 clusters, one per source state; location-specific 2022 hourly weather; atlas/1/2 kWh daily service cases; 168 distinct hourly solves | Source building formula, selection, equal service, hourly balances and lifecycle costs checked; no measured demand or national extrapolation | Cheapest assessed option at each selected point; grid considered conditionally at ten sites and not assessed at eight beyond the 50 km local-study scope |
| **Joint recovery planning** | Four neighbouring Blue Nile clusters, 880 potential connections; shared routes, repair budgets, regional supply and three full-year mixed-integer solves | Saved binary choices, route connectivity, hourly operation, lifecycle costs, budgets and optimality gap checked | Conditional local repair/connect/off-grid plans; aggregate regional boundary, not yet a national allocation |
| **National supply coupling** | Eight neighbouring clusters, 978 potential connections, 11 candidate edges and a 19-node national supply model; three local recovery cases | Local/national hourly balances, hydro budgets, clock alignment, costs and coupling bounds checked | Conditional access choices supplied by the national fixed-fleet reference; not national universal access or national rehabilitation investment |

**Calibration is not independent validation.** Matching inputs does not confirm the network or operation. The 2012 report's forecasts for 2022 are not observations. The 2025 Atlas combines inputs from different years: demand is a building formula and conflict labels describe 2020–2022, not current safety.

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
  report_evidence/               Curated PDF evidence, usage guide, source issues and checks
  system_costs/                  Editable component costs, quantities, scenarios, sources and cost coverage
  electrification_pilot/         Three source clusters, cached hourly weather, provenance and pilot assumptions
  electrification_uncertainty/   Experiment ranges, joint scenarios and interpretation rules
  spatial_proxy_study/           18-state sample, building-demand scenarios, cached weather and coverage
  recovery_planning/            Four neighbouring clusters, candidate routes and three recovery conditions
  national_coupling/            Eight clusters, sparse route graph and frozen national reference
research/forecasting_2012/
  Sudan_Forecasting_Replication.ipynb   Historical analysis notebook
  data/                          Canonical extracted historical CSVs
  results/                       Recalculated outputs and source issues
  SOURCE_REGISTER.md             Original data owners and links
  DATA_DICTIONARY.md             Units, definitions and extraction rules
research/dre_atlas_2025/
  Sudan_DRE_Settlements.ipynb    Executed spatial evidence notebook
  data/                          Settlement attributes and display polygons
  SOURCE_REGISTER.md             Layer dates, rights and limitations
  prepare_data.py                Rebuild from original public downloads
research/system_costs/
  Sudan_System_Costs.ipynb       Single notebook for system-cost accounting and sensitivities
  cost_model.py                  Reusable fixed-design lifecycle-cost engine
  pilot_model.py                 Hourly capacity optimization using full lifecycle costs
  uncertainty_model.py           Cached re-optimization and break-even calculations
  spatial_proxy_model.py         Full-year comparison across selected state-spanning source clusters
  recovery_model.py              Joint hourly service, route, repair and shared-hub optimization
  coupled_model.py               National dispatch coupling with checked cost bounds
  results/                       Budgets, annual ledger, sensitivities and numerical checks
scripts/                         Catalog maintenance
.github/workflows/               Automated execution and integrity checks
```

Use the [data collection](data/README.md) for input evidence. Use [2022 results](results/) or [historical results](research/forecasting_2012/results/) for calculated outputs. **Historical and DRE inputs are not yet coupled to the 2022 model.** The evidence register identifies the remaining reconciliation work.

## Next milestone

The [spatial proxy-demand study](data/spatial_proxy_study/README.md) now continues with available evidence across 18 states, following the [pilot](data/electrification_pilot/README.md) and [uncertainty analysis](data/electrification_uncertainty/README.md). Next computational steps are alternative hourly activity profiles at matched daily energy, multi-year weather/fixed-design tests, and larger spatial strata with shared-route decisions. These can proceed without measured settlement demand. Local demand, quotations and engineering evidence can strengthen later claims; their absence must remain explicit. See the [milestones and completion criteria](docs/STUDY_PLAN.md#milestones-and-completion-criteria).

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

# Spatial atlas integrity and maps
python research/dre_atlas_2025/check_data.py
python research/dre_atlas_2025/run_notebook.py --kernel pypsa

# System-cost accounting and the single cost notebook
python research/system_costs/check_costs.py
python research/system_costs/run_notebook.py --kernel pypsa
python research/system_costs/check_pilot.py
python research/system_costs/check_uncertainty.py
python research/system_costs/check_spatial_proxy.py
```

For a new environment, use Python 3.13 and install `requirements.txt` plus the [spatial notebook requirements](research/dre_atlas_2025/requirements.txt); extracting a local PDF also needs the historical package's requirements. Add `--export-only` to a notebook runner to refresh its HTML after a markdown-only notebook edit. See [dataset maintenance](data/README.md) for data updates.

## Sources and project history

The baseline uses UNSD and World Bank sources cited in its notebook. Historical inputs have a [source register](research/forecasting_2012/SOURCE_REGISTER.md) and [rights/qualification notes](research/forecasting_2012/DATA_SOURCES_AND_RIGHTS.md). The [DRE source register](research/dre_atlas_2025/SOURCE_REGISTER.md) gives CC BY 4.0 attribution, layer dates and transformations. Original project code is MIT licensed; third-party material is not relicensed. Source PDF reports and raw page exports remain outside the public repository.

Earlier exploratory files are preserved in Git history at `legacy-before-single-notebook-20260914`. Active work is the four notebooks above. PyPSA-Sudan is an independent research project, without implied PyPSA endorsement. A paper release still needs claim-appropriate validation, broader structural/weather uncertainty and an archived reproducible version.
