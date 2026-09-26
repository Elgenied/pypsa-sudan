# Data dictionary and extraction rules

All files are UTF-8 CSV. `pdf_page` means the physical page in the supplied 139-page PDF, starting at 1. `source_id` identifies the report in `source_metadata.json`. The external implementation check has its own URL and page field. Blank numeric cells mean missing/not applicable, never an assumed zero.

## Units and conventions

- Power: MW; annual and monthly energy: GWh, unless otherwise specified.
- `_pct` columns are percentage points on a 0–100 scale, **not fractions**. Divide by 100 before using as a multiplier.
- `population_million`, `households_million` and `connected_households_million` are in millions. Locality `population_2008` and `households` are counts.
- Historical state and locality names retain PDF spelling (and sometimes joined words). No automatic crosswalk to current boundaries is implied.
- `aggregate=True` marks a subtotal/national row. Exclude these rows before summing constituent states. State forecasts include both Sudan West and Sudan total aggregates.
- Geographic coordinates are degrees north/east as printed. Route lengths are kilometres; `voltage_kv` is kilovolts. No line-rating MW is inferred from voltage or transformer MVA.
- Projection values, including fractional customer counts, are retained at the printed precision. They are not observed customer-meter records.
- The plant annex's average-generation row mixes historical values and values for future committed plants in merged cells. `generation_average_row_gwh` retains the extracted numbers; `average_row_classification` distinguishes historical from planning values. Planned-plant values are never classified as observed generation.

## Normalized tables

| File | Row key | Meaning and important caveats |
|---|---|---|
| `national_forecast.csv` | scenario, year | Wide national forecast, 2012–2031. Metric suffixes give units. `billed_gwh` is customer sales; `sent_out_gwh` is required generation after plant own-use but before grid losses. `peak_mw` is sent-out peak. |
| `national_forecast_long.csv` | scenario, year, metric | Same data with original cell text, printed unit, table row index and page. Printed rural-population unit `#` is interpreted as million because values and population identity require it; original unit preserved. |
| `state_forecast.csv` | scenario, state, year | Consumption, growth, share and coincident load. National peak here differs from national forecast pages; do not silently substitute. |
| `state_access_forecast.csv` | scenario, state, year | Grid access, off-grid target and overall access (% of households). Rounded independently; sums can differ by 1 point. Grid includes some large isolated grids in this report. |
| `historical_consumption.csv` | state, sector, year | 2006–2011 utility consumption in GWh. Includes national totals. No mapping to present 18 states. |
| `plant_characteristics.csv` | plant_id | 19 technical configurations, including unit groups and committed projects. Capacity gross/net distinction retained. O&M is USD/kW/year and USD/MWh, not fuel-inclusive marginal cost. `replacement_of` prevents counting Roseires or Sennar twice. First/last operating years are strings because some include ranges or `>2031`; future dates are plans, not confirmations. |
| `plant_historical_generation.csv` | plant_id, year, basis | Net and gross annual generation, 2007–2011. The 2011 Khartoum North 2 cell is blank; no value is copied from North 1. Planned/not-operating cells remain missing. |
| `hydro_monthly.csv` | plant_id, month | `minimum_mw`, `dependable_mw`, `firm_mw`, `mean_generation_mwh_per_day`. Eight configurations, including replacements. These are separate hydrological planning statistics, not an hourly inflow model. |
| `hydro_monthly_long.csv` | plant_id, month, metric | Long form of the same hydro values. |
| `thermal_heat_rates.csv` | plant_id, load_pct | Net heat rate in kJ/kWh for 11 thermal groups at 20–100% load. Efficiency fraction is 3600/heat_rate. Different efficiencies are printed elsewhere for Al Fula and Kosti. |
| `localities_2008_2012.csv` | locality_id | 2008 population/households and 2012 grid/project status. `c` means committed; `p` planned. `national_grid_2012` is yes/no, not a household electrification rate. Supply coverage is an area metric. Unconnected localities with zero distance and no route are flagged, not assumed adjacent to a live line. `nogrid` coverage percentage is retained as missing numeric rather than silently zero. |
| `state_census_2008.csv` | state | Population, households, urban/rural/nomadic shares, area and grid proximity. The original uses European number formatting, explicitly converted. Includes Sudan total. |
| `population_projection.csv` | state, year | CBS population figures reproduced in report, 2009–2031, million people. Historical-year projections are not relabelled census observations. Includes Sudan total. |
| `historical_gdp.csv` | table, series, year | Sector values in the PDF's printed million SDG at 1981/82 prices; growth series in percent. 2010–2011 are marked primary estimates. Original territorial scope requires care around secession. GDP is contextual, not a fitted model predictor here. |
| `transmission_summary_2012.csv` | voltage_kv | Number and total length of lines by voltage, not circuit rating or complete topology. |
| `planned_transmission_routes_2012.csv` | state, route | 37 planned routes, lengths and voltage. Status is as assessed in 2012. `thermal_rating_mw` is deliberately missing. Main-text committed/under-construction project tables are also available in raw extractions, not normalized line records. |
| `annual_supply_balance.csv` | scenario, year | Available capacity, peak, reserve and energy balances. Negative gap means deficit; reserve deficit is not simulated unserved energy. |
| `monthly_supply_balance.csv` | scenario, year, month | Same conceptual quantities at monthly resolution, using the source's differing reserve convention. February–December 2031 capacity entries are blank. `capacity_missing_in_pdf` identifies them. |
| `source_register.csv` | source_key | Original source owners, vintage, report pages, availability, related links and limitations. |
| `implementation_crosscheck_2019.csv` | plant_id | Later World Bank project implementation evidence. Status date is 2019, not today or 2022. |

## Local-only unverified material

When extraction is rerun with a local source PDF, `raw_tables_unverified/` contains every table detected by pdfplumber, with a page-numbered filename. Detection can split one visual table into multiple files, fuse columns, or capture only headers. `raw_table_inventory.csv` lists dimensions; “98 tables” means 98 extraction blocks, not 98 uniquely validated source tables.

The local-only `plant_geometric_rows_unverified.csv` preserves coordinate-aligned rows on p.120 to assist further checking. Small vertical text offsets can split a printed row into multiple records. Prefer normalized plant tables for analysis.

The normalized extraction uses explicit page/table/row mappings and assertions. Original national numerical cell values are retained in the national long table. Raw files are local-only and ignored by Git. The `n ` prefix leaking from a p.132 label into the first Moderate required-capacity cell is removed explicitly. No source discrepancies are silently reconciled.

## Derived outputs

`results/demand_reconstruction.csv`, `annual_balance_recalculated.csv` and `monthly_balance_recalculated.csv` distinguish computed columns from printed inputs. Hydro and thermal reconciliation tables expose discrepancies. `annual_monthly_comparison.csv` preserves differences across annexes. `validation_checks.csv` documents tolerances; `source_issues.csv` records non-rounding problems. The notebook is the executable calculation specification.
