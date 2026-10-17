# Report evidence for Sudan electricity planning

**Start here:** these files improve the evidence base for a least-cost recovery and electrification study. They do **not** change the 2022 dispatch model or constitute a new optimized recovery plan.

Reviewed on **17 October 2026**. The supplied folder contains **19 PDF files, representing 18 distinct documents**. The two sustainability-unit PDFs contain the same article. We reviewed the energy-relevant methods, tables, definitions and limitations; broad development reports also contain material outside this study. The forecasting report and DRE technical report reuse their existing, checked collections.

## What to use first

| Question | Files | What they provide | How to use them |
|---|---|---|---|
| What equipment can run in a dated wartime scenario? | [plant_status_2024.csv](plant_status_2024.csv) | 20 asset records from the World Bank's August 2024 snapshot, with causes and four explicitly stated available-MW values | Construct an **August 2024** availability scenario; distinguish fuel/staff shortages, maintenance and damage. Do not assume these conditions persisted to 2026. |
| What did the historical fleet contain? | [plant_inventory_2019.csv](plant_inventory_2019.csv), [darfur_plants_2012.csv](darfur_plants_2012.csv) | 20 existing and 12 pipeline records in the 2019 diagnostic; five Darfur plants plus a total in the 2012 table | Reconcile names, units, scope and commissioning with the 2022 model. Pipeline entries are not installed assets. |
| What local equipment prices are available? | [market_prices_2025.csv](market_prices_2025.csv), [interview_prices.csv](interview_prices.csv) | 19 populated city/date quotes out of 24 possible cells, plus nine interview price records | Start a procurement-cost evidence sheet. Preserve SDG and dates; obtain matching exchange rates, warranty/specification and installed-cost scope before using in optimization. |
| What does wartime fuel cost look like? | [fuel_prices_2024.csv](fuel_prices_2024.csv) | August 2024 indicative prices and availability for six locations/groups | Test fuel-price and fuel-access scenarios separately; a missing price is not zero. |
| What drives delivery cost? | [import_cost_shares_2025.csv](import_cost_shares_2025.csv), [scenario_evidence.csv](scenario_evidence.csv) | 22 cost shares for one shipment; qualitative delay, staffing, quality and fuel constraints | Identify project cost components and scenario mechanisms. The shares are **not** a percentage uplift to apply to panel prices. |
| How much electricity do different customers use? | [sector_sales_customers.csv](sector_sales_customers.csv), [appliance_ownership_2014.csv](appliance_ownership_2014.csv) | National sector sales/customer accounts for 2015-2017; connected-household appliance ownership | Build historical sector profiles and compare demand assumptions. These are served sales, not latent demand, household counts or settlement loads. |
| What are useful published technical assumptions? | [study_parameters.csv](study_parameters.csv) | 47 rooftop, irrigation, utility PV/wind and CSP assumptions | Literature replication and sensitivity bounds. Foreign/global benchmarks and old local quotations remain explicitly labelled. |
| Can productive loads matter? | [irrigation_weather_sites.csv](irrigation_weather_sites.csv), [irrigation_model_results.csv](irrigation_model_results.csv) | 12 weather-station references and 24 published HOMER solutions for three-hectare irrigation cases | Design agricultural pilot cases and benchmark outputs. Coordinates locate weather stations; outputs are not measured loads or a fresh replication. |
| What about utility-scale CSP? | [csp_candidate_zones.csv](csp_candidate_zones.csv), [csp_model_results.csv](csp_model_results.csv) | Six candidate zones and 12 solar-only simulated outcomes, including water use | Longer-term technology screening. Candidate sites are not existing plants; Spanish reference costs are not Sudan installed costs. |
| What network evidence exists? | [network_evidence.csv](network_evidence.csv) | Historical aggregate lengths by voltage, interconnection capacity, PPA quantities and reported imports | Cross-check scale and trade scenarios. This does not provide individual routes, thermal ratings, impedances or damage locations. |
| What targets or precedents can frame scenarios? | [ndc_electricity_targets.csv](ndc_electricity_targets.csv), [programmes_and_projects.csv](programmes_and_projects.csv), [darfur_investment_plan.csv](darfur_investment_plan.csv) | Five electricity-related NDC measures, programme outputs/proposals and 16 historical Darfur investment items | Define policy and implementation scenarios. Targets, programme budgets and delivered outputs must remain distinct. |
| What historical economic benchmarks exist? | [tariffs_2018.csv](tariffs_2018.csv), [thermal_fuel_use_2017.csv](thermal_fuel_use_2017.csv), [generation_plan_comparison.csv](generation_plan_comparison.csv), [system_indicators.csv](system_indicators.csv) | Tariff blocks, fuel tonnes, historical planning results, access/loss/demand indicators and import-price context | Compare against historical evidence. A subsidized tariff is not the economic cost of supply; a forecast is not an observation. |

## Read these before modelling

- [REVIEW.md](REVIEW.md): report-by-report findings, exclusions, and the immediate modelling plan.
- [DATA_DICTIONARY.md](DATA_DICTIONARY.md): units, missing values, joins and PyPSA mapping.
- [source_register.csv](source_register.csv): every source file, title, URL where available, SHA256, review scope and duplicate handling.
- [source_issues.csv](source_issues.csv): **25** unresolved source issues; contradictions are preserved.
- [data_source_leads.csv](data_source_leads.csv): **17** leads to underlying data, with acquisition status and next action.
- [validation.json](validation.json): schema, source/page checks, LF-normalized hashes and **23** arithmetic comparisons.

The collection contains **23 evidence tables**, plus the source register, issue register and source-lead table: **26 CSV files** altogether. There are **444 records excluding the 19-row source register**. These are heterogeneous records, not 444 independent observations. Totals, missing quote cells, study assumptions and source issues are included in that count.

### The strongest immediate additions

1. The 2024 World Bank annex identifies **which plants were constrained and why**. Kosti's explicitly reported operating capacity is 125 MW against a listed 500 MW. This supports a dated fuel-limited scenario, not a claim that 375 MW was destroyed. Many other entries say only “available” or “partially available”; their numerical availability remains blank.
2. The 2026 UNDP report gives **September-October 2025** prices for 10 kWh lithium-ion batteries: **SDG 5.0-5.4 million per item** across the reported quotes, equivalent to **SDG 500,000-540,000 per nominal kWh**. These exclude unknown installation scope and do not establish usable kWh, inverter power, lifespan or current USD cost.
3. The World Bank's 2015-2017 sector sales and customer accounts make demand assumptions easier to audit. For example, the 2017 residential table implies roughly **276 kWh/account/month**. This is an existing served-customer average, unsuitable as an automatic demand level for every new rural connection.

### Values deliberately blocked or qualified

The solar-price table prints **“590 kW” per panel**. We retained that label and did not silently change it to W or calculate a cost per kW. The 200 Ah battery interviews lack voltage. The infographic's Roseires capacity conflicts with the stronger inventories. Upper Atbara's grid assignment conflicts within the 2024 report. The 2019 revenue table has an unresolved scale issue and is not converted into financial inputs.

Arithmetic checks reproduce the selected totals except two source discrepancies: the rooftop paper's stated yield parameters calculate **3,285**, rather than **3,523 kWh/year**; the CSP paper's existing transmission lengths add to **10,020.1**, rather than **10,010.1 km**. Matching arithmetic does not independently validate plant condition, prices or published simulation results.

## Load and inspect in the existing notebook

From the repository root:

```python
from pathlib import Path
import pandas as pd

d = Path('data/report_evidence')
sources = pd.read_csv(d / 'source_register.csv')
plants = pd.read_csv(d / 'plant_status_2024.csv')
prices = pd.read_csv(d / 'market_prices_2025.csv')

# Inspect the explicit wartime availability evidence; no inferred fractions.
display(plants[['asset_name', 'status_category', 'installed_capacity_MW',
                'explicitly_reported_available_MW', 'derived_available_fraction']])

# Compare dated nominal battery prices in SDG, retaining absent quotations.
batteries = prices.query("product == 'lithium_ion_battery'")
display(batteries.pivot(index='data_period', columns='city',
                       values='derived_SDG_per_nominal_kWh'))

# Join source titles and filenames for citations using source_id.
display(plants.merge(sources[['source_id', 'title', 'filename']],
                     on='source_id', validate='many_to_one'))
```

In the Desktop report folder, use `Path('data/report_evidence')` if the notebook's working directory is that folder. The local copy contains these same tables. Other collections remain in the main repository:
[historical forecasting](https://github.com/Elgenied/pypsa-sudan/tree/main/research/forecasting_2012) and
[DRE settlements](https://github.com/Elgenied/pypsa-sudan/tree/main/research/dre_atlas_2025).

## Rebuild and maintain

`build_data.py` is the reviewed transcription source. It reconstructs the evidence CSVs; it does not infer data from arbitrary PDFs. `source_register.csv` is maintained separately when new reports are reviewed. Preserve original values, definitions and dates, record any correction separately, then run:

```shell
python data/report_evidence/build_data.py
python data/report_evidence/check_data.py --refresh
python data/report_evidence/check_data.py
```

Review the diff before accepting new hashes. Run the final command alone for an integrity check. The dedicated GitHub workflow rebuilds the tables and checks for drift. No original PDFs, raw text exports or rendered source pages are included in this public collection; they remain in the local report folder/private working cache. Source rights remain with their owners; this collection contains attributed factual transcriptions and original review notes.
