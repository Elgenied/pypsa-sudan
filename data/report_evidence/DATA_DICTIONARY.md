# Data definitions and model-use rules

## Common columns

| Field | Meaning |
|---|---|
| `record_id` | Stable table-prefixed row identifier; do not assume it is a physical asset ID |
| `source_id` | Many-to-one join to `source_register.csv`; R01 and R07 are the same article |
| `pdf_page` | One-based physical page of the supplied PDF; original filename and hash identify the exact edition |
| `reference` | Table, section or paragraph; sometimes also printed page |
| `data_period` | Observation date, historical interval, planning horizon or study vintage; deliberately not forced to one year |
| `evidence_kind` | Separates reported statistics/quotes/inventory, assumptions, projections, study results, proposals and qualitative evidence |
| `notes` | Interpretation, sample/scope limitations and transformations; part of the data, not optional decoration |

All CSVs are UTF-8 with LF newlines. A blank numeric cell means **not provided or not safely interpretable**, never zero. Explicit reported zeros remain zero. Percentages use 0-100; fractions use 0-1. `is_total` is text `True`/`False`; exclude totals when adding component rows. Missing quotations are retained to distinguish absent observations from zero prices. Reported names/spellings are preserved or minimally disambiguated by technology; no geographic join is assumed.

## Units and important table-specific fields

| Table / fields | Definition and interpretation |
|---|---|
| `market_prices_2025`: `source_price_thousand_SDG`, `price_SDG` | Printed value and exact multiplication by 1,000. A price is per quoted item/specification; the panel minimum order and power unit are ambiguous. |
| `nominal_energy_kWh`, `derived_SDG_per_nominal_kWh` | Battery only: source 10 kWh; price/10. This is not usable-energy CAPEX or an installed battery-plus-inverter cost. |
| `quote_status`, `conversion_status` | Missing/reported status and whether power normalization is blocked. No USD values invented. |
| `interview_prices`: `item`, `value`, `unit` | Separate retrospective/interview quotes; do not merge with dated city quotes as if the specifications and sample were identical. |
| `import_cost_shares_2025`: `share_percent` | Share of the 22 listed costs for one five-container shipment. Repeated SSMO labels are separate line items. Denominator is not equipment purchase price. |
| `fuel_prices_2024`: `price_SDG_per_litre`, `availability` | Indicative August 2024 retail/black-market observation. For generator marginal cost, additionally obtain fuel energy content, delivered cost and electrical efficiency. |
| `plant_inventory_2019`: `installed_capacity_MW`, `category` | Printed installed or pipeline capacity. Category must be filtered before use; pipeline is not operating capacity. |
| `year_as_printed` | Exact report year field. Conflicts prevent automatically treating it as commissioning/build year. |
| `technology`, `fuel_as_printed` | Descriptive source fields. A “gas turbine” is not necessarily fueled by natural gas. SC, HCGO, HFO, LDO and DP/DO strings are retained; confirm fuel properties separately. |
| `plant_status_2024`: `explicitly_reported_available_MW` | Only explicitly quantified available/operating capacity. Blank when source says “available,” “partial,” “shut down” or damaged without a numeric MW value. |
| `derived_available_fraction` | Explicit MW / listed installed MW. Four records only. Snapshot ratio is not a measured annual capacity factor or hourly availability series. |
| `status_category`, `grid_as_printed` | Structured interpretation of source prose and printed grid island; Upper Atbara island is unresolved. Never interpret fuel/staff shutdown as destroyed assets. |
| `darfur_plants_2012`: `customers` | Historical electricity customers at plant-service level; not settlement population. |
| `sector_sales_customers`: `sales_MWh`, `customer_accounts` | National annual served electricity and customer accounts. Internal-use rows included. Derived monthly use = MWh*1,000/accounts/12. Not a household or individual average. |
| `tariffs_2018`: `SDG_per_kWh`, `USD_per_kWh_as_printed` | Source tariff columns. FX = 47.6 SDG/USD belongs only to that historical table. USD values retain the source rounding/discrepancies. Consumption block labels are preserved; block billing rules are not reconstructed. |
| `thermal_fuel_use_2017`: `quantity_tonnes` | Mass, not energy. Calorific values, unit fuel allocation and scope are needed for emissions or efficiency modelling. |
| `appliance_ownership_2014` | Percent of grid-connected households owning appliance; average units as reported. The table does not fully define the latter denominator. Watts and usage schedules missing. |
| `network_evidence`: `value`, `unit`, `voltage_kV`, `status` | Long-format lengths, interconnection MW, PPA price and reported import MW. Planned line periods overlap. kV is not a line thermal capacity. Imports in MW cannot be converted to annual GWh without duration. |
| `system_indicators`: `metric`, `value`, `unit`, `geography` | Heterogeneous historical statistics, projections, sample counts and trade-price context. Filter by metric AND period AND evidence type before comparing. Access measures have different denominators. |
| `study_parameters`: `parameter`, `value`, `unit`, `price_year` | Literature assumptions. Blank price year means not explicitly established, not the publication year. No automatic inflation/FX adjustment. |
| `irrigation_weather_sites`: `site_number`, coordinates | Join to irrigation results by site number. Latitude/longitude in degrees for nearest weather stations, not farms. Geodetic datum not specified in the table; no GIS accuracy certification. |
| `irrigation_model_results`: capacities, `battery_count`, `NPC_USD`, `COE_USD_per_kWh` | Published HOMER outputs. Battery count is not kWh. COE unit interpreted as $/kWh from context; printed table says $. `case` i/ii is the paper's ranking. Excess-generation percentage is not a loss assumption. |
| `csp_candidate_zones`: `zone`, coordinates and meteorology | Candidate-zone points; DNI kWh/m²/day, wind at **2 m**, temperature °C, elevation metres, daylight hours. Resource table is not the hourly simulation input. Join to CSP outputs by zone. |
| `csp_model_results` | Solar-only output for two reference technologies across six zones. GWh/year, CF percent, real LCOE USD/kWh for the 2021 cost case, water m³/year. Not independent measurements. |
| `ndc_electricity_targets` | Electricity displaced in 2030, avoided tCO2e and programme costs in million USD from 2021 NDC. Do not assign the entire national non-biomass emissions target to electricity. |
| `programmes_and_projects` | Count and budget scope vary by row. Planned targets, concepts, funding summaries and reported outputs have separate evidence types. Missing budgets remain blank. Beneficiaries may overlap. |
| `darfur_investment_plan` | Historical proposed phase budgets in million USD and explicit proposed MW where given. Source dashes become zero **only for phase-budget addition**. SHS scope notes: 16,500 units/year at $750/unit; not a current quotation. |
| `generation_plan_comparison` | Least-cost and government-plan forecasts for 2023 from a 2019 analysis. Capacity MW and annual GWh. Totals include import capacity; do not compare total directly with domestic-only generation assets. |
| `scenario_evidence` | Paraphrased mechanisms and modelling application. Does not assign unobserved damage probabilities, multipliers or recovery times. |
| `source_issues`, `data_source_leads` | Review findings and underlying-data acquisition plan. A named source is not a downloaded or validated dataset. |

## Translating evidence into a PyPSA study

| Model element | Candidate evidence | Required decision before use |
|---|---|---|
| Generator `p_nom` | Reconciled fleet inventory | Resolve gross/net/nameplate, commissioning, duplicates and physical unit IDs for chosen year |
| Generator `p_max_pu` | Explicit available/installed ratio and status | Define time-dependent scenario; a dated ratio alone is not a whole-year availability series |
| Generator `marginal_cost` | Delivered fuel price + variable O&M | Convert price/L to price/MWh-fuel, divide by electrical efficiency, then add VOM; preserve energy basis |
| Generator `capital_cost` | Complete installed technology quote | Annualize upfront investment using consistent real discount rate/life and add fixed O&M; convert USD/kW to USD/MW where needed |
| Storage | Battery energy quote + inverter specification | Separate energy CAPEX (per kWh) and power CAPEX (per kW), usable depth, efficiency, replacement and degradation. `Store` plus charge/discharge `Link`s can represent separate power/energy sizing |
| Loads | DRE, sector sales, appliance/crop models | Choose households, service tier, productive/critical loads, hourly profiles and displacement assumptions |
| Lines / Links | Verified routes and interconnections | Physical AC lines require electrical parameters and ratings; a controllable link approximation requires explicit justification. Existing aggregate line length cannot create topology |
| Grid extension | Route + MV/LV + transformer + meter + upstream supply cost | Include feasible routing, capacity and reliability; nearest straight-line distance is insufficient |
| Repair investments | Dated condition evidence | Add repair costs, commissioning delays and alternative asset choices explicitly; standard fixed dispatch does not decide these automatically |

Keep a separate **approved scenario input table** when modelling begins. Each chosen value should point back to one or more evidence records and state any conversion or assumption. This collection is evidence, not that approved input table.
