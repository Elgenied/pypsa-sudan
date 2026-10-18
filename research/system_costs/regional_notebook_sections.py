"""Six-state regional study in the existing reader-facing notebook."""
import nbformat as nbf

def sections():
    cells=[]
    def md(s):cells.append(nbf.v4.new_markdown_cell(s.strip()))
    def code(s):cells.append(nbf.v4.new_code_cell(s.strip()))
    md('''<a id="regional-study"></a>
## 12. Northern–central Sudan: six-state recovery study

**Start here for the regional run.** Northern, River Nile, Khartoum, Gezira, White Nile and Sennar contain **11,268 source atlas clusters and 10,078,666 potential building connections**. All are represented in 36 planning zones; a separate 48-zone run checks spatial aggregation. These are source building counts, not observed households or newly connected customers.

**Question:** where, and under which recovery conditions, do grid restoration with local support, mini-grids or standalone systems provide the required electricity service at least modelled lifecycle cost?

This model selects whole-zone service portfolios and four candidate backbone repairs while dispatching the 19-node national reference over **8,760 hours**. Local equipment designs are sized beforehand and held fixed during regional selection. The optimality statement covers that finite candidate library and assumed network; it does not cover unrestricted equipment sizing, surveyed feeder routing, or a field-validated reconstruction plan.

The local designs use PV/batteries, diesel backup for mini-grids, and grid imports for grid portfolios. Mini-grid diesel energy is capped at 20% of annual delivered service; standalone and grid portfolios have no local diesel. Local wind, small hydro and demand response are not assessed.
''')
    code('''import regional_model as regional
from check_regional import evaluate as regional_check
from regional_analysis import make as regional_figures
import contextlib, io
regional_summary=regional.run()
with contextlib.redirect_stdout(io.StringIO()):
    regional_validation=regional_check()
    regional_findings=regional_figures()
REGIONAL_OUT=regional.OUT
regional_zones=pd.read_csv(regional.DATA/'zones_36.csv')
regional_choices=pd.read_csv(REGIONAL_OUT/'all_zone_choices.csv')
regional_base=regional_summary.query("zones == 36 and demand_factor == 1 and thermal_cost_factor == 1")
display(Markdown(f"**Completed:** {len(regional_summary)} full-year regional cases: {regional_validation['feasible_cases']} feasible plans and {regional_validation['infeasible_benchmarks']} explicitly labelled infeasible benchmarks. {regional_validation['normalized_local_designs']} normalized local designs sized with {regional_validation['weather_points']} zone weather points cover all six states and all source cluster IDs. Independent saved-output checks passed."))
for r in regional_base.query("policy == 'mixed'").itertuples():
    shares=[f"{label} {100*getattr(r,mode+'_connections')/r.potential_connections:.1f}%" for mode,label in [('grid','grid with local support'),('mini_grid','mini-grid'),('standalone','standalone')]]
    display(Markdown(f"**{r.scenario.capitalize()}:** {', '.join(shares)} of potential building connections; **{r.annual_system_cost_USD/1e9:.3f} billion USD/year** including national background operation. All modelled hourly demand is served."))
display(Markdown('These are conditional choices among fixed candidate designs. Start with the coverage/accounting below before interpreting any individual point on the map.'))
''')
    md('''### 12.1 Coverage and demand accounting

The source clusters are split geographically within each state and assigned to declared regional supply buses. Northern uses Dongola and Merowe; River Nile uses Atbara; Khartoum, Gezira, White Nile and Sennar use Khartoum, WadMedani, Kosti and Sennar respectively. These are aggregate interfaces, not verified local substations.

The 2017 report's residential share of listed sector sales is applied to the 2022 reference consumption at those buses. That residential energy is allocated to zones by potential building connections. Each zone receives the larger of its allocated residential energy and **1 kWh per potential connection per day**. This is a planning allocation, not measured local demand or a census of existing access.

We remove the allocated residential share and its proportional historical accounting losses from the national loads, then serve the complete local target using the selected portfolio and its explicit losses. Other-sector demand and all outside-region loads stay in the national model. The same target is used for all policy comparisons. A separate +20% target run is clearly labelled.

Local hourly shapes are synthetic; existing national demand is aligned from Sudan local time to UTC as in section 11. Weather uses one 2022 NASA POWER hourly point per planning zone, fetched at the zone's connection-weighted centroid; the earlier run used one point per state. The table below gives each zone's farthest source cluster from its own point and from the earlier state point. This is a gridded product sampled once per zone for one year, not weather for every settlement, and Northern_03 still contains outlying desert clusters far from its point.
''')
    code('''display(regional_zones.groupby('state').agg(zones=('zone_id','size'),source_clusters=('clusters','sum'),potential_connections=('connections','sum'),allocated_existing_residential_MWh=('baseline_residential_MWh','sum'),target_MWh=('target_MWh','sum'),uplift_MWh=('uplift_MWh','sum')).reindex(regional.CONFIG['states']).style.format(precision=1,thousands=','))
regional_weather=pd.read_csv(regional.DATA/'weather_proxies.csv')
display(regional_weather.query('zones == 36')[['zone_id','geohash','lat','lon','maximum_cluster_distance_km','state_proxy_geohash','state_proxy_maximum_cluster_distance_km']].style.format(precision=1).hide(axis='index'))
display(Image(filename=str(REGIONAL_OUT/'regional_choices_map.png')))
''')
    md('''### 12.2 Recovery projects and fair comparisons

Four schematic corridors are offered for rehabilitation: Merowe–Khartoum, Atbara–Khartoum, Khartoum–Wad Medani and Khartoum–Kosti. Their initial available capacity is assumed to be 10% of the reference rating. Repair restores the reference rating. These projects test a recovery mechanism motivated by dated reports; they are **not identified damaged assets**.

The assumed upfront repair cost is **70,000 USD per proxy route kilometre plus 2 million USD per corridor for terminal works**; proxy length is great-circle length ×1.3. Costs are analyst allowances, not quotations. They use a 20-year life and 2% annual O&M. Unlike the earlier local pilot, HV repair is not costed as an MV feeder.

| Recovery case | Backbone repair rule | Local feeder outage hours, Sudan time |
|---|---|---|
| Restricted | No repair budget | 18–23 |
| Selective | Optimize repairs within 45 million USD | 19–21 |
| Restored | All four projects restored | None scheduled |

The three cases alter both backbone opportunities and local availability; their differences do not isolate a causal repair-budget effect. Each is evaluated with a mixed portfolio, grid-led service, and decentralized-first service. Feasible plans must also supply the rest of the country, with no shortage generator. If a benchmark is infeasible, a separate diagnostic allows explicitly labelled unserved energy at a 1 million USD/MWh penalty. That penalty is a diagnostic device, not a welfare valuation; the failed benchmark has no reported feasible system cost. Failure applies to the fixed candidate design and assumed network, not every possible grid-led investment plan.

Diagnostic shortfall is system-wide, including national background loads; it is not allocated to particular households or interpreted as observed outages. The penalty-based diagnostic estimates shortfall with resource costs present, rather than solving a separate exact lexicographic minimum-unserved-energy problem.

Local grid and mini-grid distribution costs sum each source cluster's length proxy; they do not assume one enormous state-wide mini-grid or free shared feeders. Local physical schedules can be divided proportionally among the member clusters because weather and service shape are common within each zone. Shared inter-cluster mini-grid routing is not optimized. A 35% refurbishment allowance is applied to the demand-weighted existing share of applicable wiring/grid assets; this is not observed infrastructure condition.

Civil works, applicable fuel tanks and the provisional 1,000 USD/year network-site protection allowance are counted per source cluster. The protection allowance is not a current security assessment; it is zero for standalone systems.
''')
    code('''display(pd.read_csv(regional.DATA/'corridor_register.csv').query('candidate_repair')[['asset_id','reference_MW','available_fraction','route_proxy_km','repair_initial_USD']].style.format(precision=2,thousands=','))
display(Image(filename=str(REGIONAL_OUT/'regional_state_pies.png')))
display(regional_base[['scenario','policy','status','unserved_MWh','shortfall_hours','grid_connections','mini_grid_connections','standalone_connections','annual_system_cost_USD','repair_investment_USD','initial_local_and_repair_USD']].style.format(precision=0,thousands=',',na_rep='—'))
display(Image(filename=str(REGIONAL_OUT/'regional_costs.png')))
display(Markdown('**Local equipment totals.** Capacities are summed replicated systems, not a single plant or battery spanning disconnected settlements. Grid imports are delivered at the national/local interface.'))
display(pd.read_csv(REGIONAL_OUT/'state_capacities.csv').groupby('scenario').sum(numeric_only=True).reindex(regional.CONFIG['scenarios']).style.format(precision=1,thousands=','))
display(Markdown('**Local annual energy flows (MWh).** The state pies above count connections, not energy. Grid-labelled zones can still obtain substantial energy from local PV. Battery discharge is stored energy and must not be counted as a new primary source.'))
display(pd.read_csv(REGIONAL_OUT/'state_energy.csv').groupby('scenario').sum(numeric_only=True).reindex(regional.CONFIG['scenarios']).style.format(precision=1,thousands=','))
display(Markdown('**National supply (MWh), including background demand outside the study area.** Accounting cancellation and diagnostic unserved energy are excluded from physical generation.'))
national_energy=pd.read_csv(REGIONAL_OUT/'national_physical_generation.csv')
display(national_energy[national_energy['case'].isin(regional_base.query("policy == 'mixed'")['case'])].pivot(index='scenario',columns='carrier',values='MWh').reindex(regional.CONFIG['scenarios']).style.format(precision=1,thousands=','))
for result in regional_base.query("policy == 'mixed'").itertuples():
    display(Markdown('**'+result.scenario.capitalize()+' — selected backbone projects**'))
    display(pd.read_csv(REGIONAL_OUT/result.case/'repairs.csv')[['asset_id','selected','spend_USD']])
''')
    md('''### 12.3 What the cost and reliability claims mean

Costs use the existing constant-2025-USD lifecycle ledger, 10% real discounting and a 20-year horizon. They include local investments/replacements/O&M, backbone repair annualization, and **the national background operating bill**. They are not incremental access-only costs and cannot be compared directly to section 11's totals. Historical sunk national capital is excluded. Grid portfolio sizing uses an illustrative 140 USD/MWh supply price; that charge is removed from local costs before actual national dispatch cost is added.

The national model retains its fixed 2022 fleet, illustrative marginal costs, fixed imports/other output and schematic corridor ratings. Monthly hydro upper bounds use historical 2012 report shapes normalized to the 2022 annual energy limits. This adds seasonality but does not establish measured 2022 inflows or reservoir dynamics. Thermal fuel shortages are not inferred from plant destruction.

Every selected portfolio's saved hourly power balance, cyclic storage, equipment limits, local losses and outage service are checked at its **fixed installed capacities**. Its grid imports are matched to national dispatch in every hour. There is no time aggregation, and no capacity resizing during verification. This establishes deterministic adequacy for the declared year and schedules, not outage probabilities, voltage compliance or N−1 security.

The regional MIP targets a 0.05% gap for its finite candidate set. The local designs are not re-sized in response to national marginal prices; alternative designs could improve the result outside this library. Whole-zone decisions can conceal differences within a zone. The maps therefore show inherited zone choices rather than individual settlement recommendations.
''')
    code('''display(pd.read_csv(REGIONAL_OUT/'independent_checks.csv').style.format(precision=7))
display(pd.DataFrame([regional_validation]))
display(Markdown('**Solver bounds.** For infeasible benchmarks these bounds apply to the penalized shortfall diagnostic, not a feasible resource-cost plan.'))
display(regional_summary[['case','status','mip_gap','lower_bound_USD','objective_USD','target_residential_MWh','uplift_MWh']].style.format(precision=3,thousands=','))
''')
    md('''### 12.4 Focused robustness checks and research use

The selective mixed case is rerun at 48 zones, at +20% residential service, and at +25% thermal/delivered diesel fuel price (local diesel O&M unchanged). The fuel-price case re-prices the fixed local candidate designs; it does not create newly optimized local designs. The 48-zone case uses its own 48 weather points, so it changes grouping and weather sampling together. These are three focused checks, not probability estimates. The first table reports both cost changes and the potential connections whose inherited technology changes.

The second table is the weather-resolution comparison: the same twelve cases and service targets solved with the earlier one-point-per-state weather (frozen reference run, commit c509ef0) and with one NASA POWER point per zone. It reports the cost change, the connection shares, the zones and potential connections whose inherited mode changes, and the farthest-cluster distances before and after. It isolates the weather-sampling change only; other weather years and products are untested.

It also reports the chosen repair projects: similar total costs do not guarantee stable discrete investment choices, and a small solver gap is not evidence that an individual repair priority is robust.

This is an executed six-state **scenario study** with complete source coverage and a reproducible finite-portfolio comparison. Before making construction recommendations or claiming a definitive least-cost regional plan, refine the grid/tie-in evidence, weather coverage, demand/access allocation, candidate design diversity and local routes. The results can support a methodological paper with these limits explicit; running the model alone does not establish publication readiness.
''')
    code('''display(pd.read_csv(REGIONAL_OUT/'focused_checks.csv')[['case','annual_system_cost_USD','cost_change_percent','selected_repairs','clusters_changing_mode','potential_connections_changing_mode','connection_change_percent']].style.format(precision=2,thousands=','))
display(Markdown('**State-proxy versus per-zone weather.** Blank costs are infeasible benchmarks, compared by diagnostic unserved energy instead.'))
display(pd.read_csv(REGIONAL_OUT/'weather_resolution_check.csv')[['case','annual_system_cost_state_weather_USD','annual_system_cost_zone_weather_USD','cost_change_percent','unserved_state_weather_MWh','unserved_zone_weather_MWh','grid_share_state_weather_percent','grid_share_zone_weather_percent','zones_changing_mode','potential_connections_changing_mode','connection_change_percent','maximum_cluster_distance_state_weather_km','maximum_cluster_distance_zone_weather_km','median_zone_maximum_distance_state_weather_km','median_zone_maximum_distance_zone_weather_km']].style.format(precision=1,thousands=',',na_rep='—').hide(axis='index'))
display(Markdown('[Regional method and source assumptions](../../docs/REGIONAL_MODEL.md). Inputs: `data/regional_model`; outputs: `research/system_costs/results/regional`. Run `regional_model.py` and `check_regional.py`, or Run All here. Cached results are hash-checked; edited inputs require re-solving.'))
''')
    return cells
