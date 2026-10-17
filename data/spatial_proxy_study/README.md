# Available-data spatial electrification study

Read **section 9** of the existing [system-cost notebook](../../research/system_costs/Sudan_System_Costs.ipynb). It continues the study using available public inputs and explicit demand scenarios; measured settlement demand is not a prerequisite for this stage.

## Evidence and scope

The World Bank Group / VIDA [Sudan DRE Atlas](https://energydata.info/dataset/sudan-distributed-renewable-energy-dre), 2025 release, CC BY 4.0, supplies source clusters, building counts, modelled daily demand, solar resource and line proximity. These are mixed-vintage proxies, not observations of current customers, access, damage or safety. See the [atlas source register](../../research/dre_atlas_2025/SOURCE_REGISTER.md). No private/customer data are added.

This extension selects **one actual cluster in each of 18 states**, from 6,843 eligible clusters in the 33,891-cluster atlas. It is a deterministic geographical sample, not random sampling and not a representative state or national sample. Twenty-one atlas records lack a state label and cannot enter the state-stratified selection. Counts, total costs and generation additions must not be extrapolated to Sudan.

Eligibility: 80–250 potential connections; known state; positive area, demand and solar resource; density 0–25%; nonnegative line distance; finite selection features; no detected source nightlight. Absence of nightlight does not establish lack of electricity. Names may be placeholders; source geohashes identify exact records. No conflict-risk label is used for selection or as a present-day damage/safety assessment.

Within each state, transform connection count, hull area and grid distance with `log1p`, retain annual solar yield untransformed, centre each feature on its median, and divide by its interquartile range (use one if the range is zero). Choose the actual record with the smallest sum of squared deviations, breaking ties by geohash. Selection is independent of costs/results. This deliberately samples small clusters near the state's eligible median feature profile; it does not cover all settlement types.

## Demand and service scenarios

| Case | Daily delivered electricity | Interpretation |
|---|---|---|
| `atlas_proxy` | Published `demand` kWh/day, divided by potential connections to set the model's per-point load | Source building formula, not metered consumption |
| `recovery_1` | 1 kWh/potential connection/day | Analyst-selected service target |
| `recovery_2` | 2 kWh/potential connection/day | Higher-service target |

The atlas formula is `1.1 * large_buildings + 0.65 * medium_buildings + 0.335 * small_buildings` kWh/day. Its daily total is rounded to one decimal. We preserve the published total and independently check the formula within its rounding tolerance. Potential connections equal eligible building counts, not surveyed households. Very small structures are not added to service points.

All options receive the same assumed hourly demand shape and annual delivered energy within each case. The shape remains the pilot's evening-heavy profile; no measured diversity, seasonal loads or productive demand is introduced. Service cases are separate steady-state systems, not an investment timeline or predicted recovery trajectory. Higher service does not imply that actual demand or willingness to pay will reach the target.

## Supply and grid coverage

Standalone and mini-grid designs use the unchanged hourly PyPSA/lifecycle-cost engine. Each is optimized for every demand case at every selected location. Mini-grid diesel remains capped at 20% of delivered annual energy. Costs, discount rate, replacement lives and supply assumptions are the central pilot inputs; geography affects source demand, resource and network length proxies, not spatially varying equipment prices or logistics.

The grid alternative is conditionally assessed only where source straight-line line proximity is **at most 50 km**. This is a declared scope cutoff, not a physical feasibility boundary. Ten selected clusters pass; eight do not. For an assessed candidate, use the pilot's assumed 80 kW usable tie-in, 1.3 route multiplier, constant losses and provisional network costs. Compare continuous availability with a six-hour daily interruption from 18:00 through 23:59 local. No surveyed tie-in, route, line voltage or upstream spare capacity is established, even inside the cutoff.

Beyond the cutoff, grid is **not assessed**, rather than assigned infinite cost. The cheapest displayed alternative is only the cheapest among the two off-grid options. Regional reconstruction, a new shared backbone, existing isolated grids or another supply point could change the result. A state map must never imply these alternatives have been ruled out.

The experiment contains 168 distinct full-year cases: 108 off-grid problems (18 sites × three demand cases × two architectures), plus 60 grid problems (ten sites × three demand cases × two availability cases). Off-grid results are reused in both grid-comparison scenarios. Maps display 108 comparison points across panels, not 108 different settlements.

## Weather and dates

Each site has complete 2022 hourly GHI and ambient temperature from the [NASA POWER hourly API](https://power.larc.nasa.gov/docs/services/api/temporal/hourly/), explicitly requested in UTC. Source GHI is Wh/m² over the hourly interval, numerically equal to average W/m² for that one-hour interval. Temperature is °C. No gaps are filled; all 8,760 timestamps and sentinel values are checked. The pilot's horizontal-array conversion, temperature coefficient and efficiency assumptions remain unchanged. Gridded weather is not local station validation or a tilted-panel yield model.

The mixed-vintage atlas and 2022 weather are deliberately combined as public planning inputs. This is **not an observed 2022 settlement electricity system**, a current population inventory or a prediction of the end of the war. The annual pattern repeats over the central 20-year constant-2025-USD lifecycle horizon. There is no demand growth, PV degradation trajectory or battery lifetime uncertainty in this extension; those remain additional scenario dimensions.

## Files

- `design.json`: explicit selection, demand and grid scope settings.
- `sites.csv`: selected source attributes and separately named derived fields (demand per point, formula check, selection score, grid scope and sample IDs).
- `coverage.csv`: source/eligible/selected cluster counts by state, without expansion weights.
- `selection_manifest.json`: source and derived hashes, selection method and attribution.
- `atlas_context_points.csv.gz`: source IDs and coordinates for background map context only; no supply choices for unselected sites.
- `weather_<geohash>_2022.csv.gz`: cached hourly inputs.
- `weather_<geohash>_source.json`, `weather_manifest.json`: exact requests, API metadata, units, source and file hashes.

Outputs in `research/system_costs/results/spatial_proxy/`:

- `summary.csv`: optimized capacities, costs, generation and numerical residuals for every distinct case.
- `cases/<case_id>/`: complete hourly results plus exact model/input fingerprints.
- `scenario_choices.csv`, `scenario_options.csv`: comparisons under each demand/grid case; explicit `grid_assessment` and `assessed_options` fields.
- `sample_option_counts.csv`, `sample_totals.csv`: descriptive counts and sums for these 18 sites only.
- `demand_choice_changes.csv`, `findings.json`: changes in the cheapest assessed option.
- `independent_checks.csv`, `validation.json`: source/formula, equal-service, hourly-balance, operating-limit and lifecycle-cost checks.
- Three figures: point maps, state-labelled sample matrix, and demand/grid-coverage diagnostics.

“Lowest cost” always means among the modelled options and assumptions. Continuous capacities, fixed losses, the AC-coupled standalone architecture, its purchasing premium and the fixed backup-ready mini-grid site costs remain potential structural sensitivities. Costs include the framework's assumed nonrecoverable tax allowance; they are not a tax-excluded national welfare optimum. The 5% near-tie screen is an analyst convention, not statistical confidence.

## Reproduce and continue

From the project root in the existing `pypsa` environment:

```shell
python research/system_costs/spatial_proxy_model.py
python research/system_costs/check_spatial_proxy.py
python research/system_costs/spatial_proxy_analysis.py
python research/system_costs/build_notebook.py
python research/system_costs/run_notebook.py --kernel pypsa
```

Normal notebook runs are offline and reuse content-checked solutions. Input/model changes invalidate caches. `spatial_proxy_model.py --force` rebuilds tables, reusing identical checked individual cases. The baseline pilot and uncertainty outputs are separate and remain unchanged.

Explicit source refresh: `python research/system_costs/prepare_spatial_proxy.py` requires the repository atlas and internet; it reselects sites and caches verified weather. Use `--selection-only` to inspect selection first. Do not interpret a successful numerical check as validation of actual demand or surveyed network feasibility. The Desktop copy contains all required study inputs; the full-atlas selection is rechecked when the full atlas is present, while selection provenance/source rows and output checks remain available offline.

Further computational work can proceed without measured loads: alternative appliance/activity profiles at fixed daily energy, multiple weather years, fixed-design stress testing, larger stratified samples and shared-route decisions. Empirical evidence can refine these assumptions later; its absence limits claims rather than halting the scenario study.
