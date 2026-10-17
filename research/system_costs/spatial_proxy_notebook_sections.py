"""Available-data spatial extension in the existing single study notebook."""
import nbformat as nbf

def sections():
    cells=[]
    def md(s):cells.append(nbf.v4.new_markdown_cell(s.strip()))
    def code(s):cells.append(nbf.v4.new_code_cell(s.strip()))
    md('''<a id="spatial-proxy-study"></a>
## 9. Continue with available data: a state-spanning proxy-demand study

**We can study electrification choices without a measured settlement-demand series.** This section uses the public atlas's building-demand estimate as one explicit scenario, then tests two chosen recovery-service levels. Missing measured demand is a model limitation, not a prerequisite for running this stage.

The study selects **18 actual atlas clusters, one in each state represented in the source**, before looking at costs. It obtains each selected location's complete 2022 NASA POWER hourly weather, sizes supply options and compares equal delivered service. The sample adds geographical breadth to sections 7–8; it is not a statistically representative national sample.

**What this answers:** how local supply choices change across these source locations and assumed service levels. **What it does not establish:** the cheapest technology for an entire state, a national investment budget, current electrification status or a forecast of observed post-war demand.
''')
    code('''from spatial_proxy_model import run as run_spatial_proxy, DATA as SPATIAL_DATA, OUT as SPATIAL_OUT, DESIGN as SPATIAL_DESIGN
from check_spatial_proxy import check as check_spatial_proxy
from spatial_proxy_analysis import analyse as analyse_spatial_proxy
spatial_results = run_spatial_proxy()  # Offline checked caches; changed inputs trigger new solves.
spatial_validation = check_spatial_proxy()
spatial_views = analyse_spatial_proxy()
spatial_sites = pd.read_csv(SPATIAL_DATA/'sites.csv')
spatial_coverage = pd.read_csv(SPATIAL_DATA/'coverage.csv')
spatial_selection = json.loads((SPATIAL_DATA/'selection_manifest.json').read_text())
display(Markdown(f"**Coverage:** {spatial_selection['selected_clusters']} selected clusters from {spatial_selection['eligible_clusters']:,} eligible clusters in an atlas of {spatial_selection['atlas_clusters']:,}. The model solved **{spatial_validation['unique_hourly_cases']} distinct full-year cases**, covering **{spatial_validation['checked_case_hours']:,} case-hours**. Only the selected points receive technology comparisons."))
display(spatial_sites[['sample_id','admin_cgaz_1','geohash','num_connections','demand',
                      'atlas_daily_kWh_per_connection','distance_to_existing_transmission_lines','grid_in_local_scope']]
       .rename(columns={'admin_cgaz_1':'Source state','num_connections':'Potential connections',
                        'demand':'Atlas proxy kWh/day','grid_in_local_scope':'Grid assessed conditionally'})
       .style.format({'atlas_daily_kWh_per_connection':'{:.3f}','distance_to_existing_transmission_lines':'{:.2f}'}))
''')
    md('''### 9.1 Sampling and demand assumptions

Eligible records have 80–250 potential connections, positive area/demand/solar resource, building density between 0% and 25%, a state label and no detected source nightlight. Placeholder place names are retained; geohashes identify the sites. Within each state, choose the actual record nearest the median feature profile for building count, area, line distance and solar yield. Count, area and distance are transformed with `log1p`; features are divided by their within-state interquartile range and squared deviations are summed. Ties are broken by geohash. Selection does not use costs or model outcomes.

This deliberately restricts the study to comparable small clusters. It excludes many large towns and small settlements; a chosen site does not represent all communities in its state. No nightlight is not proof of no electricity. Source nightlights span September 2022–August 2023, and source buildings/labels have mixed dates.

| Demand case | Daily energy | How to interpret it |
|---|---|---|
| **Atlas proxy** | Source formula: 1.1 × large + 0.65 × medium + 0.335 × small buildings, kWh/day; retain published rounding | Building-based low-service estimate, not metered demand |
| **Recovery 1** | 1 kWh per potential connection per day | Chosen service target; not a forecast |
| **Recovery 2** | 2 kWh per potential connection per day | Higher-service target; not an estimate of unmet demand |

All cases use the pilot's same assumed hourly shape. Building counts are potential service points, not verified customer accounts. The source formula is independently reconstructed, and every supply option receives exactly the same delivered energy and hourly shape within a demand case. Higher-service scenarios are separate steady-state systems; they do not model a gradual investment or demand-growth trajectory.

The **2022 weather year is a common resource reference**, combined with the 2025-release mixed-vintage settlement atlas. These inputs do not constitute an observed 2022 settlement electricity system.
''')
    md('''### 9.2 Grid-assessment scope

The source gives straight-line distance to mixed/unknown-voltage line geography. It does not identify a functioning tie-in. We conditionally evaluate the pilot's grid option only where that distance is **50 km or less**. This is an analyst scope screen, **not an engineering feasibility limit**. Within that screen we retain the unsurveyed route multiplier, fixed 80 kW tie-in and constant losses; long feeders still need a different engineering model.

For the other sites, grid is **not assessed**. Their displayed choice is only between standalone and mini-grid; shared transmission expansion, reconstruction of local grids or a different connection point could change it. No infinite grid cost or claim of grid infeasibility is assigned.

Where grid is considered, compare continuous upstream availability with the existing synthetic six-hour evening outage. Standalone and mini-grid results do not change when the upstream grid scenario changes, so the same checked solutions are reused. The mini-grid retains its 20% annual delivered-energy diesel cap.

All equipment prices and finance assumptions remain central and spatially uniform. The preceding uncertainty section tests their sensitivity. PV is still a horizontal-array approximation; distribution losses, wiring and route lengths remain the documented pilot proxies. Current damage and security conditions are not inferred from atlas conflict categories.
''')
    code('''display(Image(filename=str(SPATIAL_OUT/'proxy_demand_and_grid_scope.png')))
display(spatial_coverage)
''')
    md('''### 9.3 Spatial results at selected clusters

Colour denotes the cheapest **assessed** option. Circles include a conditional grid alternative; triangles compare only the two off-grid options. Numbers match the site table. Grey dots locate the full atlas for context; they are neither administrative boundaries nor locations with calculated supply choices. State polygons are intentionally not coloured from a single sample.
''')
    code("display(Image(filename=str(SPATIAL_OUT/'spatial_choices.png')))")
    md('''### 9.4 Demand can change the architecture

Each cell reports lifecycle cost per delivered kWh for the cheapest assessed option, with its architecture shown by colour. These are full hourly-feasible model solutions under the stated assumptions. State names below identify where the sampled cluster lies, not a recommended state-wide technology.
''')
    code('''display(Image(filename=str(SPATIAL_OUT/'state_sample_comparison.png')))
choices=spatial_views['choices']
display(spatial_views['counts'])
display(spatial_views['changes'].query("choice_changes"))
display(Markdown('Counts describe these 18 selected sites only. They are not probabilities, population shares, national technology shares or estimates of access gains. The two grid scenarios duplicate off-grid results where grid is not assessed.'))
''')
    md('''### 9.5 Costs, capacities and close alternatives

The table below shows the higher-service case with continuous grid availability where assessed. Near ties identify sites where an alternative costs within 5% of the cheapest. Full capacities, dispatch and all other scenarios are retained in the result tables.
''')
    code('''display(choices.query("demand_case=='recovery_2' and grid_case=='continuous'")[
    ['state','geohash','grid_assessment','winner_among_assessed_options','lowest_USD_kWh','runner_up_premium_percent',
     'within_5_percent','pv_kWp','battery_nominal_kWh','diesel_kW','initial_budget_USD']]
    .style.format({'lowest_USD_kWh':'{:.3f}','runner_up_premium_percent':'{:.1f}',
                  'pv_kWp':'{:.1f}','battery_nominal_kWh':'{:.1f}','diesel_kW':'{:.1f}','initial_budget_USD':'{:,.0f}'}))
display(spatial_views['totals'][['demand_case','grid_case','sampled_clusters','sample_connections',
       'sample_annual_delivered_MWh','sample_initial_budget_USD','sample_weighted_USD_kWh']]
       .style.format({'sample_annual_delivered_MWh':'{:,.1f}','sample_initial_budget_USD':'{:,.0f}','sample_weighted_USD_kWh':'{:.3f}'}))
display(Markdown('**Sample totals only:** these sums cover the 18 independent modelled clusters. They are not a Sudan budget and do not include shared feeders, regional reinforcement or population weighting.'))
''')
    md('''### 9.6 What we can conclude using available evidence
''')
    code('''findings=spatial_views['findings']
lines=[f"- The selected sites contain **{findings['sample_connections']:,} potential connections**. Grid was considered conditionally at **{findings['grid_conditionally_assessed']} sites** and not assessed at **{findings['grid_not_assessed']}**."]
for scenario,count in findings['demand_case_changes'].items():
    lines.append(f"- Moving from atlas-proxy demand to 2 kWh/connection/day changes the cheapest assessed architecture at **{count} of 18 sites**, under the **{scenario.replace('_',' ')}** grid scenario.")
for key,counts in findings['counts'].items():
    lines.append('- **'+key.replace('_',' ')+'**: '+', '.join(f'{mode.replace("_"," ")}: {number}' for mode,number in counts.items())+' sampled sites.')
if not (choices.winner_among_assessed_options=='grid_extension').any():
    lines.append('- **Grid is not cheapest in the ten conditionally assessed sites.** This sample deliberately contains small clusters with no detected nightlight, selected near eligible state feature medians. It does not cover urban demand or shared trunk investments and cannot establish that off-grid is preferable throughout Sudan. The two grid-availability maps have identical winners because grid is already more expensive here; grid-option costs still change.')
display(Markdown('\\n'.join(lines)))
display(pd.DataFrame([spatial_validation]))
''')
    md('''### 9.7 Continue without waiting for measured demand

This is now a reproducible **available-data scenario study**. The paper can frame its findings as conditional responses to service targets and available spatial evidence. It should not claim to have forecast actual customer consumption or identified a nationally optimal allocation.

The next computational improvements can also use public data and explicit scenarios:

1. Replace the single assumed hourly shape with several documented appliance/activity profiles at the same daily energy; test daylight productive loads and evening household peaks.
2. Test fixed selected designs against multiple weather years and unplanned supply failures, rather than resizing them after each uncertainty is revealed.
3. Add more sites per spatial stratum and evaluate shared routes/upstream limits before extrapolating or allocating technologies nationally.

Measured demand or local engineering evidence can strengthen the study if obtained later. Their absence remains transparent in the assumptions and uncertainty analysis rather than stopping progress.

**Reproduce:** `python research/system_costs/spatial_proxy_model.py`, then `python research/system_costs/check_spatial_proxy.py`. Normal runs use stored inputs offline. `prepare_spatial_proxy.py` is an explicit source-refresh step requiring the full atlas and internet. The detailed experiment, files, units and limits are in [the spatial proxy guide](../../data/spatial_proxy_study/README.md).

**Sources:** [World Bank Group / VIDA Sudan DRE Atlas, 2025 release, CC BY 4.0](https://energydata.info/dataset/sudan-distributed-renewable-energy-dre); [NASA POWER hourly API](https://power.larc.nasa.gov/docs/services/api/temporal/hourly/), 2022 GHI/temperature requested in UTC. Exact weather requests, units and hashes are retained with the inputs. Source formula and mixed-vintage definitions follow the project's [existing atlas source register](../dre_atlas_2025/SOURCE_REGISTER.md).
''')
    return cells
