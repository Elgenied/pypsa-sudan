# PyPSA-Sudan

**Research direction: least-cost electricity recovery and expansion of access in Sudan.**

**Current methodological decision:** [follow the Zambia study's complementary PyPSA and OnSSET branches](docs/ZAMBIA_ALIGNED_SCOPE.md), using three-hour national time steps. The settlement screen below is a prototype under correction following review; its 1,304 ranking switches should not be treated as measured benefits of grid rehabilitation.

The question is: **Where should Sudan rehabilitate or extend the grid, where should it build mini-grids, and where are standalone systems more economical—at a specified level of service?**

**Start here: [Sudan → PyPSA-Earth handover notebook](integration/pypsa_earth/Sudan_Earth_Handover.ipynb)** ([HTML](integration/pypsa_earth/Sudan_Earth_Handover.html), [WSL configuration and commands](integration/pypsa_earth/README.md)). The existing WSL engine now has a separate Sudan configuration and staged evidence. Native input/aggregation checks and the workflow dry-run pass; the full 2022 Earth model has not yet been solved.

The [OnSSET–PyPSA settlement screen](research/onsset_pypsa_recovery/Sudan_OnSSET_PyPSA_Recovery.ipynb) remains a **prototype under correction**, not the validated implementation of the revised scope. Its 11,268-settlement coverage remains useful; its recovery ranking switches are not established repair benefits.

The [one-page workspace guide](docs/WORKSPACE_GUIDE.md) explains which notebooks to open, what has been validated and what comes next. The [new study README](research/onsset_pypsa_recovery/README.md) gives exact reproduction commands and limits. The [completed full-year regional PyPSA study](research/regional_joint_study/Sudan_Regional_Joint_Study.ipynb) remains the supply-side comparison. Earlier system-cost sections, the Gezira experiment, historical forecasting and the 2022 dispatch notebook remain as supporting evidence and previous development stages.

The revised study uses complementary national PyPSA-Earth and settlement OnSSET analyses with consistent demand, service and cost definitions. Mandatory iterative price feedback is outside the agreed scope. The atlas has modeled population and potential connections, but no verified post-war settlement access status or surveyed asset damage.

## Earlier notebooks and supporting evidence

| Supporting artifact | What it tells you |
|---|---|
| **1. [Overall study plan](docs/STUDY_PLAN.md)** | Research question, grid / mini-grid / standalone comparison, PyPSA's role and milestones |
| **2. [Evidence, validation and gaps](docs/EVIDENCE_AND_GAPS.md)** | What we have, what was checked, what is assumed and what is missing |
| **3. [2022 system notebook](Sudan_2022.ipynb)** | Running dispatch model, national calibration, regional maps and stress tests |
| **4. [Historical evidence notebook](research/forecasting_2012/Sudan_Forecasting_Replication.ipynb)** | Recovered 2012-report data, replicated calculations, regional sector pies and source conflicts |
| **5. [Settlement atlas notebook](research/dre_atlas_2025/Sudan_DRE_Settlements.ipynb)** | Settlement maps, source formula checks, state summaries, grid-distance screens and spatial gaps |
| **6. [Report evidence and usage guide](data/report_evidence/README.md)** | October 2026 review: dated equipment/fuel prices, plant status, sector sales, published assumptions, source conflicts and modelling uses |
| **7. [System-cost and electrification notebook](research/system_costs/Sudan_System_Costs.ipynb)** | Previous-stage cost and planning experiments; section 12 is the earlier six-state regional plan. The active Earth handover notebook is linked above. |

The notebooks serve different stages of the research. Saved results can be viewed on GitHub without running Python. The [2022 HTML](Sudan_2022.html), [historical HTML](research/forecasting_2012/Sudan_Forecasting_Replication.html), [settlement HTML](research/dre_atlas_2025/Sudan_DRE_Settlements.html), [cost HTML](research/system_costs/Sudan_System_Costs.html) and [Gezira HTML](research/gezira_joint_planning/Sudan_Gezira_Joint_Planning.html) are browser reading copies. The full-region continuation generates its own notebook and HTML only after all 12 cases pass validation.

## What exists today

| Workstream | Available | Validation status | What it can answer |
|---|---|---|---|
| **Active Earth integration** | Sudan WSL configuration, native custom demand, plant review crosswalk, checksummed evidence, handover notebook | Native readers, three-hour energy/weight conservation and full DAG dry-run checked; no new national solve | How evidence enters the standard national workflow and what remains to reconcile |
| **Earlier OnSSET–PyPSA settlement screen** | 11,268 settlements × three recovery conditions; three native OnSSET technology cost options; saved maps, state pies and PyPSA case register | Accounting and recovery-attribution problems identified; under correction | Prototype coverage and methods only; rankings are not validated recovery recommendations |
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
| **Six-state regional study** | 11,268 clusters in 36 zones with one NASA POWER weather point per zone, three recovery conditions, four candidate backbone repairs, policy benchmarks, three focused checks and a state-versus-zone weather comparison | Full-year operations, demand accounting, cost reconstruction and finite-library optimization bounds checked; infeasible benchmarks explicitly reported | Conditional whole-zone service choices and assumed backbone repairs; not unrestricted design optimality or verified damage-based recommendations |

**Calibration is not independent validation.** Matching inputs does not confirm the network or operation. The 2012 report's forecasts for 2022 are not observations. The 2025 Atlas combines inputs from different years: demand is a building formula and conflict labels describe 2020–2022, not current safety.

## Find the right files

```text
README.md                         Project map and reading order
docs/
  WORKSPACE_GUIDE.md              Current reading order and research sequence
  STUDY_PLAN.md                   Earlier research design and milestones
  EVIDENCE_AND_GAPS.md            Evidence status, checks and missing inputs
Sudan_2022.ipynb                  Main 2022 model; inputs embedded here
Sudan_2022.html                   Reading copy of the same notebook
results/                         Generated model outputs, not new observations
research/onsset_pypsa_recovery/  Active settlement study, notebook and code
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
  regional_model/               Six-state zones, crosswalks, per-zone weather points, frozen state-weather reference and recovery assumptions
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
  regional_model.py              Six-state finite-portfolio selection and backbone recovery
  results/                       Budgets, annual ledger, sensitivities and numerical checks
scripts/                         Catalog maintenance
.github/workflows/               Automated execution and integrity checks
```

Use the [data collection](data/README.md) for input evidence. Use [2022 results](results/) or [historical results](research/forecasting_2012/results/) for calculated outputs. Section 12 combines DRE cluster counts, a reported 2017 residential sales share, historical hydro seasonality and the 2022 national reference. These are declared proxy allocations; remaining fleet, geography and demand reconciliation is recorded in the evidence register.

## Next milestone

Obtain the 2022 Earth weather cutout and standard spatial inputs, build and reconcile the national fleet/network/import baseline, then run the three recovery cases and complementary standard OnSSET access analysis. The [Earth integration guide](integration/pypsa_earth/README.md) records concrete prerequisites and WSL commands. The earlier [study plan](docs/STUDY_PLAN.md) is retained for history.

## Run

For the active WSL PyPSA-Earth workflow, use the [integration commands](integration/pypsa_earth/README.md#reproduce-in-wsl).

To reopen the earlier 2022 reference notebook in the Windows environment:

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
python research/system_costs/regional_model.py
python research/system_costs/check_regional.py
```

For a new environment, use Python 3.13 and install `requirements.txt` plus the [spatial notebook requirements](research/dre_atlas_2025/requirements.txt); extracting a local PDF also needs the historical package's requirements. Add `--export-only` to a notebook runner to refresh its HTML after a markdown-only notebook edit. See [dataset maintenance](data/README.md) for data updates.

## Sources and project history

The baseline uses UNSD and World Bank sources cited in its notebook. Historical inputs have a [source register](research/forecasting_2012/SOURCE_REGISTER.md) and [rights/qualification notes](research/forecasting_2012/DATA_SOURCES_AND_RIGHTS.md). The [DRE source register](research/dre_atlas_2025/SOURCE_REGISTER.md) gives CC BY 4.0 attribution, layer dates and transformations. Original project code is MIT licensed; third-party material is not relicensed. Source PDF reports and raw page exports remain outside the public repository.

Earlier exploratory files are preserved in Git history at `legacy-before-single-notebook-20260914`. Active work is the four notebooks above. PyPSA-Sudan is an independent research project, without implied PyPSA endorsement. A paper release still needs claim-appropriate validation, broader structural/weather uncertainty and an archived reproducible version.
