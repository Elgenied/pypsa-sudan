# Six-state regional recovery model: formulation and interpretation

Read section 12 of [the system-cost notebook](../research/system_costs/Sudan_System_Costs.ipynb). This implements the agreed Northern, River Nile, Khartoum, Gezira, White Nile and Sennar scope. The study covers every one of the **11,268 atlas source IDs**, grouped into 36 planning zones, with a 48-zone resolution comparison. The 10,078,666 potential building connections are not verified household accounts or an estimate of new connections.

## What is optimized

Each zone chooses either a grid portfolio or its cheapest independent off-grid portfolio (mini-grid or standalone). Four candidate backbone projects can restore transmission capacity, subject to the case's repair rule. The 19-node national model dispatches generation and transfers for all 8,760 hours, including demand outside the region. Local service and equipment schedules are already physically feasible hourly candidate columns.

The objective is local annualized lifecycle resource cost plus national generation operating cost plus annualized backbone repairs. The feasible-set boundary matters: the solver certifies a **finite-portfolio, whole-zone choice problem**. Local capacities are not re-optimized against endogenous national marginal costs, and unsurveyed routes are not optimized. This is a regional scenario comparison rather than an unrestricted least-cost engineering design.

For zone `z`, the binary `g_z` selects grid service. Each off-grid column serves the same target and has no shared fuel, land or investment constraints. Eliminating the more expensive of its two off-grid columns therefore preserves the finite-library optimum. The national bus receives the sum of `g_z × grid_import_z(t)`. In implementation, one fixed-profile accounting generator per zone cancels the unselected grid load exactly; its output is **not physical generation**. The independent checker reconstructs actual imports from selected portfolios and verifies this equality hour by hour.

## Coverage and demand conservation

All atlas clusters are retained, including urban and nightlight-positive sites. Within states, clusters are recursively split at spatial medians along the larger coordinate extent, starting from their assigned supply-bus group. The partitions provide a reproducible geographic aggregation; they do not identify surveyed feeders. The full source-ID-to-zone crosswalk is exported for both resolutions. Supply buses are Dongola/Merowe in Northern (nearest of those two), Atbara in River Nile, Khartoum in Khartoum, WadMedani in Gezira, Kosti in White Nile and Sennar in Sennar.

The 2017 residential share is 0.5661606534 of the sum of listed sector sales in R19 Annex 3. Applying this share to 2022 reference consumption at the seven study buses allocates **6,381,677.96 MWh/year** to local residential service. We distribute that energy in proportion to potential building connections within each bus area. The zone target is the greater of this allocated energy and 1 kWh per potential connection per day. The base regional target is **6,869,460.45 MWh/year**: an uplift of **487,782.49 MWh/year**, not the full atlas demand added to national consumption.

The allocated residential share and the same fraction of historical accounting losses are removed from the national study-bus loads. Local grid (10%) and mini-grid (8%) distribution losses are then represented in the selected portfolios; standalone has no distribution-loss multiplier. Other-sector and outside-region background loads are unchanged. Residual national accounting losses remain exogenous, rather than varying with flows. National transport corridors are lossless. These assumptions are not a measured marginal-loss model.

The original national synthetic clock is shifted from Sudan local time to UTC with the same periodic wrap as section 11. Local residential service follows the existing synthetic evening-peaking profile, with identical shape across all zones. Replacing the allocated reference residential profile preserves annual energy, not its old hourly shape. Uniform national sector shares and building-weighted allocation are explicit assumptions, not observed regional demand or access status.

## Local candidate library and costs

Four hundred and twenty normalized designs are optimized using PyPSA: one standalone, one mini-grid and three grid-availability designs for each of the 36 primary zones and each of the 48 resolution-check zones. Each normalized design supplies 1,000 kWh/day over 2022. Equipment and its feasible physical schedule scale linearly with each zone's annual service. Power limits, SOC limits, cyclic storage and the local diesel energy ceiling scale with them.

Each zone uses a 2022 NASA POWER hourly point fetched at its connection-weighted centroid: 60 distinct points serve the 84 zone rows of `weather_proxies.csv`, which also records each zone's farthest source cluster from its own point and from the earlier state point. The median zone's farthest cluster is about 70 km away at 36 zones and 60 km at 48, against 138–591 km for the one-point-per-state proxies of the earlier run, kept in `weather_proxies_state.csv` with their six files. Northern_03 still reaches 559 km because of outlying desert clusters. NASA POWER is a gridded reanalysis/satellite product (MERRA-2 and SYN1DEG sources) sampled at one point per zone for one year; it is not settlement weather, and a single weather year remains a limitation.

The assessed local technologies are PV and batteries, with diesel backup for mini-grids and grid imports for grid portfolios. Standalone and grid portfolios do not include local diesel generators. Mini-grid diesel energy is capped at 20% of delivered annual service. Local wind, small hydro, demand response and alternative storage technologies are outside this candidate set.

Common weather and demand shapes within a zone allow the normalized schedule to be distributed proportionally across its clusters. No electricity is transported between disconnected settlements by an aggregate local store. Mini-grid equipment represents systems replicated across the member clusters; **inter-cluster mini-grid routes are not selected**. Equipment is continuously divisible; household inverter module sizes, minimum generator units and electrical distribution engineering are not represented.

Local costs are rebuilt from the existing complete lifecycle ledger after scaling equipment. LV route proxy is the sum of `1.3 × sqrt(connections × hull_area_km2)` for source clusters. Grid MV proxy is the sum of `1.3 × source distance to grid`, without sharing overlapping routes. Transformer counts use the common profile peak, distribution loss and 80 kW per nominal 100 kVA unit. Civil/site and applicable tank allowances are counted per source cluster. These are screening quantities, not installed-network observations.

The provisional 1,000 USD/year network site-protection allowance is charged per source cluster for grid and mini-grid options, not once per aggregated zone. Standalone has no such network-site allowance. This is an accounting allowance, not a security assessment. The checker verifies the count independently.

The ratio of allocated existing residential energy to target service defines a refurbishment fraction: `1 − existing_share × (1 − 0.35)`. This fraction is applied to wiring, service meters and relevant grid assets; new mini-grid distribution and equipment are charged in full. It is an energy-share proxy for sunk infrastructure, not a count of previously connected buildings. Local designs use the 20-year, 10% real, constant-2025-USD ledger with taxes excluded. There is no new supplier survey in this run.

Grid portfolios are sized at an illustrative 140 USD/MWh supply cost and their declared outage schedule. That grid charge is removed before the regional objective adds actual national dispatch costs. The battery charge tie-break penalty used for local sizing is excluded from reported resource cost. National fuel prices remain the reference's illustrative assumptions. The +25% fuel case changes national combustible marginal costs and local diesel fuel cost; local designs remain fixed and local diesel variable O&M is unchanged.

## Backbone and hydro

Candidate repairs are `merowe_khartoum`, `atbara_khartoum`, `khartoum_medani` and `khartoum_kosti`. Their starting capacity is assumed to be 10% of the schematic reference rating. A binary repair restores the full reference capacity in both flow directions. Other corridors retain their reference limits. This is restricted connectivity, not a claim to reconstruct the reported electrical islands.

Each project's upfront cost is 70,000 USD per great-circle-route-km ×1.3 plus 2 million USD for terminal works. These are declared HV rehabilitation allowances, not quotations or MV costs. Annual cost uses a 20-year annuity at 10% real plus 2% of upfront cost for annual maintenance. There is no separately charged terminal project that duplicates this allowance. The repair budget covers these four projects only; it does not cap all local investment.

| Case | Repair rule | Local grid outage hours (UTC+2) |
|---|---|---|
| Restricted | No repair spending | 18–23 |
| Selective | Optimize within 45 million USD | 19–21 |
| Restored | All four projects restored and charged | None scheduled |

The fixed 2022 fleet and reference imports remain available in all cases; this is not a measured post-war fleet. The [World Bank 2024 update](https://documents1.worldbank.org/curated/en/099080625100525928/pdf/P171810-aceaafc9-7439-4838-974c-81284effd33a.pdf) motivates backbone disruption scenarios, but does not identify these particular repair costs or residual capacities. The existing evidence register retains the report's conflicting Upper Atbara island assignment; that disputed classification is not used here.

Monthly hydro upper budgets take the historical 2012 report's mean daily generation shape, multiply by 2022 month lengths and normalize to the existing 2022 annual budget for each regional hydro generator. Mappings: Merowe→M-HP, Khartoum→Jeb-HP, Roseires→Ros-HP, Sennar→Sen-HP, Gedaref→UpA-HP, Kassala→KhE-HP. These are historical/project configurations used for scenario seasonality, not validated 2022 operating units or reservoir inflows. Unused monthly allowance cannot be shifted into another month; there is no reservoir state equation.

## Experiment set and infeasibility

The run has nine main combinations (three recovery conditions × mixed/grid-led/decentralized policies) plus selective mixed cases with 48 zones, +20% residential service, and +25% fuel price. Service targets are identical within each policy comparison. The 48-zone case preserves the base target and source coverage but has its own 48 weather points, so it changes both grouping and weather sampling; it is a resolution check, not a nested refinement, and no non-increase bound is asserted for it. Exported checks quantify changes by source IDs and potential connections.

## Weather-resolution comparison

The reader-facing outputs of the earlier state-proxy run (commit c509ef0) are frozen in `data/regional_model/state_weather_reference/`. `weather_resolution_check.csv` compares the same twelve cases, with identical service targets, under state and zone weather: annual system cost, grid and mini-grid connection shares, zones/clusters/potential connections whose inherited mode changes, and the maximum and median farthest-cluster distances before and after. The checker verifies that the frozen reference covers the same cases and targets. In this run the nine feasible cases cost 0.1–0.9% less with zone weather than with state proxies, and between 8% and 21% of potential connections inherit a different mode; the selective mixed case also switches its repair selection from Merowe–Khartoum to Atbara–Khartoum plus Khartoum–Wad Medani, which illustrates that discrete repair priorities are not robust to this input change. This isolates the weather-sampling change; it does not test other weather years or products.

Feasible plans prohibit load shedding. An infeasible policy benchmark receives a separate diagnostic solve with explicitly labelled `unserved_diagnostic` generators at a 1 million USD/MWh penalty. This estimates supply shortfall for that fixed portfolio and network; it is not a physical supply asset or a value-of-lost-load estimate. The result retains an infeasible status, reports unserved energy/hours, and has a blank feasible annual system cost. Its diagnostic objective is not used to rank it as a feasible plan. Another grid-led design with more backup or different investments might be feasible outside the candidate library.

This shortfall includes national background loads and is not attributed to particular households or treated as observed outages. The diagnostic retains resource costs alongside the penalty; it is not an exact lexicographic minimum-shortfall solve.

All local sizing and national selection use 8,760 chronological hours. Verification replays the saved physical schedules at fixed installed capacities and checks national balances; it does not resize investments to hide infeasibility. The regional MIP target is 0.05% of the full objective. A zero reported gap is numerical, not an exact-arithmetic statement. Benchmark and mixed results carry their actual solver statuses and bounds.

## Reproduction and files

```bash
python research/system_costs/prepare_regional_model.py    # only to refresh frozen inputs
python research/system_costs/prepare_regional_weather.py  # only to refresh cached zone weather (NASA POWER)
python research/system_costs/regional_library.py --workers 8
python research/system_costs/regional_model.py
python research/system_costs/check_regional.py
python research/system_costs/regional_analysis.py
python research/system_costs/build_notebook.py
python research/system_costs/run_notebook.py --kernel pypsa
```

Inputs: `data/regional_model/`; results: `research/system_costs/results/regional/`. Hash-checked caches reuse identical solved cases. The study uses PyPSA 1.0.6 and HiGHS 1.12.0. Custom choices and constraints are exported separately because [PyPSA's network export does not preserve the optimization model](https://docs.pypsa.org/v1.0.6/user-guide/optimization/custom-constraints/). Rebuild with the Python model rather than re-optimizing the NetCDF alone.

Reader-facing outputs include `state_allocations.csv`, `state_capacities.csv`, `state_energy.csv`, `national_physical_generation.csv`, `focused_checks.csv`, `weather_resolution_check.csv` and the numerical validation report. Maps, state connection pies and cost comparisons are saved as PNG and SVG figures. Raw case `generation.csv` includes accounting variables; use `national_physical_generation.csv` for physical supply totals, and retain its feasibility-status column when interpreting benchmarks.

This is an executed regional scenario framework with numerical checks. Additional weather years and sub-zone weather, access/demand allocation, usable tie-ins, feasible shared routes, repair quotations and candidate design diversity remain material evidence/model gaps. Field reliability, construction recommendations, national universal-access cost and optimal multi-period reconstruction timing are outside its claims.
