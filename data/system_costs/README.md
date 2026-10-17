# System costs: inputs, scope and use

**Start with the [executed cost notebook](../../research/system_costs/Sudan_System_Costs.ipynb) or its [HTML reading copy](../../research/system_costs/Sudan_System_Costs.html).** This is a working full-cost accounting layer for fixed illustrative designs. It does not certify feasible supply or give a procurement quotation, national budget or least-cost map.

Prepared 17 October 2026. Every USD model input is a **provisional analyst assumption**, with lower-input, central and higher-input cases. Historical regional benchmarks and dated Sudan evidence are kept separate. The assigned **constant-2025-USD** basis is an explicit scenario convention, not a verified normalization of older prices. No actual or forecast currency exchange rate is assumed. Price and FX normalization remain necessary for a paper's central cost estimates.

**Next study step implemented:** section 7 of the same notebook now uses these costs in an [hourly three-cluster PyPSA pilot](../electrification_pilot/README.md). The fixed examples described below remain unchanged; the pilot separately sizes equipment and reconstructs full costs from dispatch. It produces conditional local rankings, with explicit service and route assumptions, not a field-validated plan.

## Files to edit and files to read

| File | Role |
|---|---|
| `components.csv` | 17 equipment/installed-work unit costs, ranges, lives, O&M, scope, eligibility for additional freight/labour, benchmark anchors and reasoning |
| `scenario_parameters.csv` | 24 editable assumptions for logistics, development, tax allowance, finance, fuel, supply, battery life, administration and retirement |
| `bill_of_quantities.csv` | Explicit quantities for four illustrative 100-home designs; not optimized capacities |
| `case_designs.csv` | Connections, demand, losses, diesel share and synthetic repair inputs |
| `benchmark_evidence.csv` | Seven historical benchmark rows, original units, source pages and limitations; not automatically loaded as current prices |
| `sources.json` | Source URLs, download hashes and links to Sudan report evidence |
| `coverage.csv` | What is costed, what is provisional, boundaries and requirements for upgrading each input |
| `../../research/system_costs/results/` | Generated budgets, annual ledger, sensitivities, checks and input hashes; never edit as input |

The spreadsheet-like CSVs are machine-readable model data. The notebook is the single reading/analysis interface. `build_notebook.py` rebuilds notebook structure, **not the cost inputs**. Editing canonical CSVs and running the notebook preserves your price changes.

## What “full cost” means here

The supply boundary runs from new equipment or the grid tie-in through safe basic house wiring. It includes equipment, electrical BOS, civil/site allowance, network, meters, connections, delivery, installation, development, contingency, an assumed nonrecoverable import tax, maintenance, administration, security/insurance allowances, fuel or grid purchases, replacements, retirement and the cost of capital through discounting. A separate amortizing-loan illustration shows funding and debt-service requirements.

It excludes customer appliances, productive equipment, large resettlement programmes and a countrywide transmission reconstruction plan. Grid supply is priced at the tie-in on an assumed all-in upstream supply-service basis. Do not also charge a generic upstream generation CAPEX unless replacing that service-cost boundary with an explicitly modelled upstream system. The intact-grid example assumes capacity available by definition; real sites may violate that assumption. The repair example adds only its explicit repair scope, not the historical book value of sunk assets.

All construction is booked at commissioning. Multi-year drawdown, interest during construction, working capital, tax-accounting rules and project-specific reserves need a dated financial model. Real loan rates are illustrations, not bank offers. No implicit exchange-rate stability or financing availability is claimed.

## Accounting and double-counting rules

1. **Currency and units:** prices are USD per the `quantity_unit` column. Never confuse nominal kWh with usable kWh, kW with kVA, or route km with conductor km. The 100 kVA transformer is priced per installed unit. Life is integer years. Rates are fractions (0.10 = 10%).
2. **Component prices:** PV modules, PV inverter, battery and battery inverter/EMS are separate. Standalone hybrid inverters include MPPT; the evaluator rejects also charging a standalone PV inverter. `pv_bos` includes mounting and electrical hardware. Installed line, transformer, connection and civil unit costs already include ordinary installation/delivery. Their freight/labour flags are zero.
3. **Adders:** international freight applies to imported hardware; inland logistics to flagged equipment; installation to labour-eligible equipment. Tax allowance applies to imported hardware plus international freight. Engineering applies to direct resource spending excluding tax. Contingency applies to that direct spending plus engineering, also excluding tax. No percentage is recursively applied to itself.
4. **O&M:** component maintenance fractions apply to original component prices, not inflated all-in project CAPEX. Administration, security and insurance are separate. Diesel calendar maintenance and runtime servicing have distinct scopes, subject to supplier confirmation. Fuel is priced delivered, so it receives no extra freight multiplier.
5. **Replacement:** each component is repurchased at its life before year 20; the battery scenario life overrides the component-table default. Replacements retain applicable delivery/installation, contingency and tax but omit initial development. Equipment is not replaced at the retirement boundary. Same real prices are assumed, with no learning or escalation.
6. **Retirement/residual:** removal/recycling is charged on each retired physical component, including at the study end; land rights are excluded. Baseline salvage is zero. A `salvage_fraction=1` sensitivity gives straight-line remaining service value of the delivered/installed package, excluding tax and initial development. This is a modelling credit, not a resale guarantee. Retirement is still charged conservatively.
7. **Discounting:** NPC includes year-0 investment and discounted annual operations, replacements, retirement and residual credit. EAC uses the study-horizon annuity. `conditional_USD_per_target_kWh` divides NPC by discounted **target** energy, which has not been demonstrated feasible. It is not a validated LCOE.
8. **Finance:** NPC is unlevered; debt service is not added a second time. Debt/equity/grants sum to the initial investment. Grants change sponsor funding, not underlying system cost. The collection-adjusted recovery charge is a simplified equivalent annual cost divided by collected target kWh, not a tariff, affordability assessment or full project-finance return.

Demand is 100 homes × 1 kWh/day for all examples, constant over 20 years. No productive/critical loads, growth, seasonal solar, degradation of delivery or outage chronology are simulated. Annual diesel energy is an explicit 10% assumption for the mini-grid, not a dispatch result. New PV/storage sizes are fixed examples and may be over- or undersized. Same annual demand does **not** establish equivalent reliability or peak service. No technology is declared the winner.

## Source use

- **Sudan R17:** [UNDP 2026 solar value-chain report](https://www.undp.org/sites/g/files/zskgke326/files/2026-05/undp-sdn-solar_energy_value_chain_study_0.pdf), original PDF pages 29/31, contains dated 2025 SDG quotations. Use [existing extracted prices](../report_evidence/market_prices_2025.csv) without changing raw evidence. The printed panel power-unit issue blocks its per-kW conversion; battery voltage/specification issues also remain. Market prices can already include freight/import costs: do not apply the ex-works adders unchanged to a local retail quote.
- **Sudan R12:** [World Bank electricity snapshot](https://documents1.worldbank.org/curated/en/099080625100525928/pdf/P171810-aceaafc9-7439-4838-974c-81284effd33a.pdf), PDF pages 9–10, contains indicative August 2024 SDG fuel evidence. It is neither a current delivered USD price nor a guaranteed fuel supply.
- **ESMAP2022:** historical multi-country mini-grid benchmarks, Table 1.4, PDF page 85 / printed page 57. Cost component scope informs the ledger. The distribution lower-percentile unit appears inconsistent and is deliberately not used. Percentiles describe individual components, not a coherent optimized design.
- **WB_SOUTH_SUDAN2023:** South Sudan prospectus, Annex Table 4, PDF pages 27–28. These are another country's historical model assumptions, not Sudan's measured network prices. They remain context only except the explicitly provisional diesel central assumption. The original transformer parameter refers to HV/MV; it is not our 100 kVA MV/LV unit.
- **A01:** author-selected assumptions filling remaining gaps. The range is a planning stress range, not a statistical confidence interval or conflict probability. No source is claimed to support the exact values.

Original source PDFs are not redistributed. Factual benchmark transcriptions retain attribution and source hashes. Author code is covered by the repository license; third-party source rights remain with their owners.

## Run and change

From the repository root, in the `pypsa` conda environment:

```shell
python research/system_costs/check_costs.py
python research/system_costs/run_notebook.py --kernel pypsa
```

Or open `research/system_costs/Sudan_System_Costs.ipynb` and Run All. No internet or PDF originals are needed. The engine uses Python's standard library; the notebook additionally uses the existing pandas, matplotlib and Jupyter packages.

For a one-off sensitivity:

```python
import sys
sys.path.insert(0, 'research/system_costs')
from cost_model import evaluate
result = evaluate('grid_extension', quantity_overrides={'mv_line': 10})
result['summary']
```

This changes the route quantity, not the capacity or dispatch. Update inputs with consistent designs, price basis and scope. Use chronological PyPSA sizing/dispatch and network feasibility before making a location recommendation. Fixed network/connection costs require explicit choice logic; they are not raw USD/kW `capital_cost` values. The notebook explains units and the separate storage-energy and inverter-power mapping.
