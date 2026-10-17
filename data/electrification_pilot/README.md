# Three-cluster electrification pilot

**Read section 7 of the [existing system-cost notebook](../../research/system_costs/Sudan_System_Costs.ipynb)** or its [HTML view](../../research/system_costs/Sudan_System_Costs.html#optimized-pilot). The cost framework and the next study step remain in one notebook.

## Data versus assumptions

`sites.csv` contains selected, unchanged source attributes from the World Bank Group / VIDA [Sudan DRE Atlas](https://energydata.info/dataset/sudan-distributed-renewable-energy-dre), 2025 release, CC BY 4.0. Credit the original providers; detailed definitions and layer vintages are in the [existing source register](../../research/dre_atlas_2025/SOURCE_REGISTER.md). Geohashes, rather than reverse-geocoded labels, identify the exact clusters:

| Type | Cluster | Source label | Source state | Potential connections |
|---|---|---|---|---:|
| Near grid | scbmu9pc3u | Al Kurumuk | Blue Nile | 196 |
| Remote compact | sdxk3ns4zh | Ash Shiqeyyab | Gezira | 132 |
| Remote dispersed | sfcc38ee31 | Al Gash | Kassala | 123 |

Selection was deterministic and done before examining costs. Eligible clusters have a non-placeholder name, known state, 80–250 potential connections, positive area, building density below 25%, and no detected source nightlight. The near-grid sample is the first geohash within 1–3 km of a source line. Remote samples are within 15–35 km: the highest density above 10% and the lowest below 2%, with geohash tie-breaking. This is illustrative sampling, not national statistical representation. Absence of nightlight does not prove lack of service; source labels do not describe the whole named town. No security label was used as a present-day safety or damage assessment.

Three `weather_<geohash>_2022.csv.gz` files retain complete NASA POWER hourly GHI and ambient temperature for 2022. The [NASA API](https://power.larc.nasa.gov/docs/services/api/temporal/hourly/) was requested explicitly in UTC. Source units are Wh/m² per hourly interval and °C; the hourly radiation number is numerically its average W/m² over that hour. `source_manifest.json` records exact URLs, API metadata, underlying MERRA2/SYN1DEG source labels, coordinates, raw response hashes and derived file hashes. These are gridded satellite/reanalysis products, not local weather-station validation. No gaps were filled: all three inputs have 8,760 consecutive hours and no missing/sentinel values.

`config.json` contains all pilot design assumptions. They include demand, UTC+2 local demand timing, PV temperature/efficiency approximation, storage limits, geometric route multipliers, supply losses, fuel limit, outage hours, grid tie-in and generous capacity bounds. Monetary inputs come from [system_costs](../system_costs/README.md), retaining their provisional status.

## Study method

1. Assign **1 kWh/day to each potential connection**, using the same assumed evening-heavy hourly shape. This replaces neither the lower source demand column nor a customer survey. All architectures receive the same hourly delivered load. Distribution losses add generation requirements for network options.
2. Estimate total new MV length as 1.3 times source straight-line distance. Estimate total LV branch length as `1.3 * sqrt(service_points * area_km2)`. No routing, voltage drop, line loading, conductor selection or power-flow certification is claimed. The 100 kVA transformer/80 kW grid tie-in is an assumed capacity boundary, not an observed usable asset.
3. Transform hourly GHI and temperature into a **horizontal-array screening PV profile** using the explicit NOCT, temperature coefficient and loss factors. This is not a tilted-plane model or a calibrated PVWatts/atlite result. Compare annual yields diagnostically to the atlas; do not force agreement across different periods/configurations.
4. Optimize continuous PV kWp, nominal battery kWh, converter AC kW and, for mini-grids, diesel kW. PV is AC-coupled with a separate PV inverter, whose assumed rating equals DC array kWp. Storage uses a `Store` and two `Link`s. Charge capacity equals discharge electrical-output capacity, the two flows share one converter rating, and converter cost is charged once. SOC is cyclic over the full year. No free initial stored energy is supplied.
5. Every hour's specified load must be served. No load shedding, export, electricity sales or negative-price revenue is permitted. Mini-grid diesel generation is capped at 20% of annual delivered demand. The annual fuel limit does not model delivery dates, storage or simultaneous fuel/equipment outages.
6. Optimize using **annualized complete lifecycle costs**, derived by exact linear increments of the existing cost ledger. Fixed network, site and customer costs are included in final comparison. Fuel and grid purchases are replaced with actual dispatch. The objective is checked against a separately reconstructed 20-year ledger. A 0.001 USD/MWh charge-flow tie-break cost is deducted from reported financial totals.

For standalone, identical profiles and weather make the aggregate solution equivalent to identical independent systems at each service point. No diversity/sharing benefit is introduced. Imported equipment has an explicitly assumed 25% small-order premium. Packaged hybrid/DC products and discrete equipment sizes could change its cost; the current architecture uses separate PV and battery converters. Mini-grid and grid options include a prepared site/civil allowance even if some optional generation equipment is not selected. The backup-ready mini-grid includes its tank/ATS allowance even in a no-fuel stress. There is no fixed-charge binary optimization within each architecture.

The three architectures are optimized separately and their complete costs ranked. Shared feeders, decisions between settlements, national dispatch feedback and an investment timeline are not jointly optimized. This is a local comparison conditional on a usable upstream grid and its assumed supply price; it is not a national optimum.

## Runs and outputs

The 18 solves cover three base options at all three clusters; a six-hour daily evening grid outage at each cluster; no diesel access at each mini-grid; and doubled demand for all three options at the compact cluster. Capacities are re-optimized for each case. The 2022 weather/demand pattern is repeated over the 20-year cost horizon; there is no multi-year weather validation, degradation trajectory or growth path.

Generated outputs are in `research/system_costs/results/pilot/`:

- `summary.csv`: capacities, investment, NPC, LCOE, generation/imports and residuals for every solve.
- `*_hourly.csv.gz`: complete chronological demand, generation, grid availability, charging/discharging and SOC.
- `selected_components.csv` and `lifecycle_cashflows.csv`: full purchase quantities and annual cost ledger.
- `checks.csv`, `independent_checks.csv`, `validation.json`: model residuals and reconstructed checks.
- `run_manifest.json`: exact model/input fingerprints, output hashes and PyPSA version.
- Figures embedded in the notebook: option costs, supply pies and hourly dispatch/SOC.

“Modelled LCOE” now uses dispatch that satisfies the specified hourly service requirement. It remains dependent on provisional input prices, routes, weather conversion and service assumptions, not a validated customer tariff or field reliability guarantee.

## Run and maintain

With the repository's `pypsa` environment (PyPSA 1.0.6, HiGHS 1.12.0):

```shell
python research/system_costs/pilot_model.py --force
python research/system_costs/check_pilot.py
python research/system_costs/run_notebook.py --kernel pypsa
```

The notebook normally checks and reuses cached results. Changed model/data fingerprints trigger fresh optimization; set `FORCE_PILOT=True` in the notebook to force it. It needs no internet for normal runs. A new source download requires the full repository atlas file and explicit `python research/system_costs/prepare_pilot.py`; this regenerates selected sites, weather and default configuration. Preserve edited configuration before refreshing. Fetching sources requires `requests`.

The numerical checks cover 157,680 hourly case snapshots, matching service, AC/SOC balances, PV/converter/diesel/grid limits, fuel budgets, prohibited grid imports during outages, absence of simultaneous battery charging/discharging, no binding design-size caps, and cost reconciliation. They verify the implementation, **not independent validity of the source data, prices or model structure**.
