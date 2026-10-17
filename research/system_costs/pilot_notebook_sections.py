"""Reader-facing pilot study appended to the existing system-cost notebook."""
import nbformat as nbf

def sections():
    cells=[]
    def md(s):cells.append(nbf.v4.new_markdown_cell(s.strip()))
    def code(s):cells.append(nbf.v4.new_code_cell(s.strip()))
    md('''<a id="optimized-pilot"></a>
## 7. Next study step: optimize supply for three real settlement clusters

**This section advances beyond the fixed illustrative budgets above.** It sizes PV, batteries and converters, dispatches every hour of 2022, and compares three supply arrangements at the **same assumed service level**. The LP's annual objective includes the complete lifecycle-cost framework, not just equipment purchase prices.

We selected three atlas clusters before examining costs: near-grid, remote compact and remote dispersed. These are illustrative cases, not a representative national sample. Names are reverse-geocoded labels; the geohash identifies the actual cluster. Potential connections are building proxies, not verified households. Absence of detected nightlight does not prove lack of electricity.

The study uses **real source coordinates and hourly NASA POWER weather**, with **assumed demand, routes, costs and grid service**. There is no post-war field validation or present-day safety assessment. Conditional rankings are meaningful within this model, not construction recommendations.

This section reuses checked cached optimization outputs when inputs are unchanged. Set `FORCE_PILOT=True` below to solve again. Changing cost inputs, pilot configuration, weather or model code invalidates the cache and triggers fresh solves. Downloading new source data is a separate explicit step.
''')
    code('''from pilot_model import run as run_pilot, DATA as PILOT_DATA, OUT as PILOT_OUT, CONFIG as PILOT_CONFIG
from check_pilot import check as check_pilot
FORCE_PILOT = False
pilot = run_pilot(force=FORCE_PILOT)
pilot_validation = check_pilot()
sites = pd.read_csv(PILOT_DATA/'sites.csv')
display(sites[['pilot_type','geohash','village_name','admin_cgaz_1','num_connections','demand',
               'distance_to_existing_transmission_lines','hull_area']].rename(columns={
               'num_connections':'Source potential connections','demand':'Source demand kWh/day',
               'distance_to_existing_transmission_lines':'Straight-line grid distance km','hull_area':'Area km2'}))
''')
    md('''### Matched service and technical assumptions

| Input | Treatment in this pilot |
|---|---|
| Demand | 1 kWh/day per source potential connection; identical evening-heavy daily shape, repeated all year; no random diversity. This is a chosen recovery-service target, **not measured demand or the lower atlas demand formula**. |
| Standalone | Identical independent AC-coupled PV/battery systems per service point. The aggregate LP is equivalent to assigning every point the same proportional system and dispatch. Equipment receives an explicit 25% small-order premium. No household diesel. |
| Mini-grid | Shared PV/battery/converter plus optional diesel generation, capped at 20% of delivered annual demand. Fixed backup-ready tank and site costs are included even if diesel is unused. |
| Grid | A fixed 80 kW usable tie-in, local PV/battery allowed, no diesel; source initially available all hours. The tie-in rating assumes a 100 kVA transformer at 0.8 power factor. This is a boundary condition, not a measured grid capability. |
| Network | New MV route proxy = 1.3 × straight-line source distance. Total LV branch-length proxy = 1.3 × √(service points × settlement area in km²). These are editable geometric assumptions, not surveyed feeders. Constant downstream losses: 8% mini-grid, 10% grid. |
| PV profile | NASA POWER hourly GHI and ambient temperature for 2022, UTC. Horizontal-array approximation: cell temperature from an assumed 45°C NOCT; −0.4%/°C temperature coefficient, 90% miscellaneous DC factor and 96% inverter efficiency. No tilt/transposition or measured calibration. |
| Battery | Separate nominal energy and converter power; 10–90% SOC, 95% efficiency in each direction, cyclic full-year state of charge. AC charge and discharge ratings share one converter; it is charged once. |
| Reliability | Every hourly demand must be supplied; no load-shedding option. No reserve, component failures, N−1 test or measured outage trace. Passing this requirement means model adequacy for these assumptions. |
| Economics | Same central 20-year lifecycle assumptions, replacements and real 10% discount rate as the cost section. Dispatch replaces the old assumed diesel share/grid purchases. The 2022 weather/load year repeats for economic accounting; no demand growth or technology degradation trajectory. |

PV capacity is expressed in DC kWp with AC output profiles. The proxy assumes a 1:1 PV inverter rating. Batteries remain nominal kWh. Solar-home systems use separate AC PV and battery converters here; a packaged DC/hybrid design could cost less and should be tested later.
''')
    code('''base_pilot=pilot.query("scenario=='base'").copy()
case_names={'standalone':'Standalone','mini_grid':'Mini-grid','grid_extension':'Grid + local PV/storage'}
site_names=sites.set_index('geohash').apply(lambda s: f"{s.village_name} [{s.name}]",axis=1).to_dict()
display(base_pilot[['geohash','mode','annual_delivered_kWh','pv_kWp','battery_nominal_kWh','converter_AC_kW','diesel_kW',
                    'initial_budget_USD','modelled_LCOE_USD_per_kWh']].style.format({
                    'annual_delivered_kWh':'{:,.0f}','pv_kWp':'{:.1f}','battery_nominal_kWh':'{:.1f}',
                    'converter_AC_kW':'{:.1f}','diesel_kW':'{:.1f}','initial_budget_USD':'{:,.0f}',
                    'modelled_LCOE_USD_per_kWh':'{:.3f}'}))
price_grid=base_pilot.pivot(index='geohash',columns='mode',values='modelled_LCOE_USD_per_kWh').reindex(sites.geohash)
fig,ax=plt.subplots(figsize=(11,5),layout='constrained')
price_grid.rename(columns=case_names).set_axis([sites.set_index('geohash').loc[k,'village_name']+'\\n'+k for k in price_grid.index]).plot.bar(ax=ax,rot=0,color=['#436C9C','#299E93','#DDAA32'])
ax.set_ylabel('Modelled lifecycle USD / delivered kWh');ax.set_xlabel('Atlas cluster (not the whole named town)')
ax.set_title('Hourly-feasible options under provisional prices and routes')
ax.legend(title='',frameon=False,fontsize=9)
fig.savefig(PILOT_OUT/'option_costs.png',bbox_inches='tight');plt.show()
ranked=base_pilot.sort_values('modelled_LCOE_USD_per_kWh').groupby('geohash',sort=False).head(2)
rows=[]
for sid,g in ranked.groupby('geohash'):
    g=g.sort_values('modelled_LCOE_USD_per_kWh');first,second=g.iloc[0],g.iloc[1]
    rows.append({'Cluster':site_names[sid], 'Conditional lowest-cost option':case_names[first['mode']],
                 'USD/kWh':first.modelled_LCOE_USD_per_kWh,
                 'Next-option premium %':100*(second.modelled_LCOE_USD_per_kWh/first.modelled_LCOE_USD_per_kWh-1)})
display(pd.DataFrame(rows).style.format({'USD/kWh':'{:.3f}','Next-option premium %':'{:.1f}'}))
display(Markdown('A “remote compact” label does not predetermine a mini-grid winner. Local distribution, load size, household equipment pricing and weather can change the ranking. No national extrapolation is made.'))
''')
    md('''### Generation mixes and seasonal storage operation

The pies show annual generation/imports for the conditionally cheapest base-case option at each cluster. Storage discharge is **not** added as new generation. The weekly plot shows all energy flows for the compact site's mini-grid, including charge below the axis and battery SOC. Every hour of the year is solved; the displayed week is selected only for readability.
''')
    code('''winners=base_pilot.loc[base_pilot.groupby('geohash').modelled_LCOE_USD_per_kWh.idxmin()]
fig,axes=plt.subplots(1,3,figsize=(12,4.2),layout='constrained')
for ax,(_,r) in zip(axes,winners.iterrows()):
    vals=np.array([r.pv_generation_kWh,r.diesel_generation_kWh,r.grid_import_kWh])
    mask=vals>1e-5
    ax.pie(vals[mask],labels=np.array(['PV','Diesel','Grid'])[mask],colors=np.array(['#E4AC32','#8D6F59','#487BA6'])[mask],
           autopct='%1.0f%%',wedgeprops={'edgecolor':'white'},textprops={'fontsize':10})
    ax.set_title(r.source_name+'\\n'+case_names[r['mode']],fontsize=11)
fig.suptitle('Annual supply mix | conditional base-case winners',fontsize=13)
fig.savefig(PILOT_OUT/'pilot_supply_pies.png',bbox_inches='tight');plt.show()

sample=base_pilot.query("pilot_type=='remote_dense' and mode=='mini_grid'").iloc[0]
hourly=pd.read_csv(PILOT_OUT/(sample.run_id+'_hourly.csv.gz'),parse_dates=['time_UTC']).set_index('time_UTC')
week=hourly.loc['2022-08-01':'2022-08-07']
fig,axes=plt.subplots(2,1,figsize=(12,6),sharex=True,layout='constrained',gridspec_kw={'height_ratios':[2,1]})
axes[0].stackplot(week.index,week.pv_MW*1000,week.diesel_MW*1000,week.discharge_MW*1000,
                  labels=['PV','Diesel','Battery discharge'],colors=['#E4AC32','#8D6F59','#269E93'])
axes[0].fill_between(week.index,0,-week.charge_MW*1000,color='#90C9C1',label='Battery charging')
axes[0].plot(week.index,week.bus_load_MW*1000,color='#202D3A',linewidth=1.5,label='Load including distribution loss')
axes[0].set_ylabel('kW');axes[0].legend(ncol=3,fontsize=9,frameon=False)
axes[0].set_title(sample.source_name+' mini-grid | one displayed week of an 8,760-hour solution')
axes[1].plot(week.index,week.battery_soc*100,color='#269E93');axes[1].set_ylim(0,100)
axes[1].set_ylabel('SOC (%)');axes[1].set_xlabel('UTC time; assumed local time is UTC+2')
fig.savefig(PILOT_OUT/'pilot_dispatch_week.png',bbox_inches='tight');plt.show()
''')
    md('''### Recovery stresses: the model chooses different capacities

These are **re-optimized cases**, not post-processing price multipliers:

- **Evening grid interruption:** grid unavailable from 18:00 through 23:59 local time every day. It is a synthetic outage stress, not a measured wartime schedule; local PV/battery can respond.
- **No diesel:** the mini-grid cannot consume diesel; PV and batteries must cover the entire year. This represents a fuel-access boundary, not an inferred damage fraction.
- **Double demand:** the compact site receives 2 kWh/service point/day for all three architectures. Routes, customers and prices remain fixed.

The full run contains 18 optimizations: 9 base options, 3 interrupted-grid cases, 3 no-diesel mini-grids and 3 higher-demand options. The remaining cost uncertainties are not resolved by these tests.
''')
    code('''stress=pilot.query("scenario!='base'").copy()
refs=base_pilot[['geohash','mode','equivalent_annual_cost_USD','modelled_LCOE_USD_per_kWh']].rename(columns={
     'equivalent_annual_cost_USD':'base_annual_cost','modelled_LCOE_USD_per_kWh':'base_LCOE'})
stress=stress.merge(refs,on=['geohash','mode'],validate='many_to_one')
stress['annual_cost_change_percent']=100*(stress.equivalent_annual_cost_USD/stress.base_annual_cost-1)
display(stress[['geohash','mode','scenario','pv_kWp','battery_nominal_kWh','initial_budget_USD',
                'modelled_LCOE_USD_per_kWh','annual_cost_change_percent']].style.format({
                 'pv_kWp':'{:.1f}','battery_nominal_kWh':'{:.1f}','initial_budget_USD':'{:,.0f}',
                 'modelled_LCOE_USD_per_kWh':'{:.3f}','annual_cost_change_percent':'{:.1f}'}))
display(Markdown('When demand doubles, annual cost and cost per kWh can move in different directions because fixed network/site costs are spread across more energy. This is not evidence of measured future demand.'))

near=sites.query("pilot_type=='near_grid'").iloc[0].geohash
compact=sites.query("pilot_type=='remote_dense'").iloc[0].geohash
def pilot_price(sid,mode,scenario):
    return pilot.query('geohash==@sid and mode==@mode and scenario==@scenario').iloc[0].modelled_LCOE_USD_per_kWh
display(Markdown(f"""**What this run teaches us:**

- At the near-grid cluster, grid supply costs **${pilot_price(near,'grid_extension','base'):.2f}/kWh** with the assumed continuous upstream service, increasing to **${pilot_price(near,'grid_extension','evening_outage'):.2f}/kWh** with evening interruptions. Standalone supply is **${pilot_price(near,'standalone','base'):.2f}/kWh**. Distance alone is therefore insufficient to choose a connection.
- At the compact cluster, the base mini-grid costs **${pilot_price(compact,'mini_grid','base'):.2f}/kWh**, versus **${pilot_price(compact,'standalone','base'):.2f}/kWh** for standalone. At double demand these become **${pilot_price(compact,'mini_grid','double_demand'):.2f}** and **${pilot_price(compact,'standalone','double_demand'):.2f}/kWh**. Demand assumptions can change the preferred architecture.
- These are conditional model responses. The study has not measured either location's real outage pattern, demand, customer count or quoted system costs.
"""))
''')
    md('''### What is now checked—and what the next paper milestone needs

The pilot checks source hashes, complete hourly inputs, identical service targets, AC energy balance, chronological battery balance, SOC/converter limits, grid-outage restrictions, diesel-energy limits, and reconstructed lifecycle cost against the optimization objective. It also checks that removing fuel or grid availability cannot lower the optimized annual cost. A tiny 0.001 USD/MWh charge-flow tie-break penalty is excluded from reported financial costs. Source counts and names remain unverified.

An optimal LP solution does **not** validate current access, prices, field reliability, safety or routes. Before location recommendations:

1. Verify the three clusters' present buildings/customers and obtain hourly household, clinic, school and productive-use demand. Replace identical profiles with measured diversity and peaks.
2. Survey a usable grid tie-in and routes, conductor/transformer capacity, repair scope and outages. Replace the geometric lengths and flat losses with distribution design and power-flow checks.
3. Obtain comparable local quotations, exact battery specifications/lifetimes and finance terms. Test modular equipment and integrated solar-home packages, not only continuous capacities and the assumed small-order premium.
4. Use a validated tilted-PV model and multiple weather years; add component failures, maintenance and reserve requirements. Test actual fuel delivery limitations and multi-year demand/recovery timing.
5. Expand the sample, include shared feeders and productive loads, and test joint investment decisions. Do not extrapolate the three conditional winners into a national technology map.

The current comparison answers: **“Under these documented service, cost, weather and network assumptions, how should each candidate architecture be sized, and what does it cost?”** It is now a functioning pilot study rather than a list of example bills.
''')
    code('''display(pd.DataFrame([pilot_validation]))
display(pilot[['max_power_balance_error_MW','max_storage_balance_error_MWh','annual_cost_objective_gap_USD']].abs().max().to_frame('Largest residual across 18 solves'))
display(base_pilot[['geohash','mode','pv_yield_proxy_kWh_per_kWp','atlas_longrun_yield_kWh_per_kWp']].drop_duplicates('geohash')
        .style.format({'pv_yield_proxy_kWh_per_kWp':'{:,.0f}','atlas_longrun_yield_kWh_per_kWp':'{:,.0f}'}))
display(Markdown('The annual solar columns have different weather periods and array assumptions. They are a diagnostic comparison, not a calibration target. Detailed hourly outputs, installed quantities and 20-year cash flows are in `results/pilot/`.'))
''')
    md('''### Pilot sources and reproducibility

- [World Bank Group / VIDA Sudan DRE Atlas](https://energydata.info/dataset/sudan-distributed-renewable-energy-dre), 2025 release, CC BY 4.0; [existing project provenance](https://github.com/Elgenied/pypsa-sudan/blob/main/research/dre_atlas_2025/SOURCE_REGISTER.md). Selected source rows are retained unchanged in `data/electrification_pilot/sites.csv`.
- [NASA POWER hourly API](https://power.larc.nasa.gov/docs/services/api/temporal/hourly/): 2022 GHI and temperature, explicitly requested in UTC. Request URLs, parameter units, API metadata, source/derived hashes and the selected coordinates are in `source_manifest.json`. Hourly radiation is Wh/m² over each one-hour interval, numerically equivalent to its average W/m² here.
- Cost evidence and assumptions remain in `data/system_costs/`; model configuration and selection rules are in [the pilot input guide](../../data/electrification_pilot/README.md).

To solve explicitly from the project root: `python research/system_costs/pilot_model.py --force`. To recalculate saved results' checks: `python research/system_costs/check_pilot.py`. To regenerate this entire reading copy: `python research/system_costs/run_notebook.py --kernel pypsa`.
''')
    return cells
