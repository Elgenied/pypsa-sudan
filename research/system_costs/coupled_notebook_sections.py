"""Current reader-facing national-coupling study, appended to the single notebook."""
import nbformat as nbf

def sections():
    cells=[]
    def md(x):cells.append(nbf.v4.new_markdown_cell(x.strip()))
    def code(x):cells.append(nbf.v4.new_code_cell(x.strip()))
    md('''<a id="national-coupling"></a>
## 11. Eight settlements, shared routes and national supply

**Current study — start here.** We now connect the local electrification choices to the 19-node Sudan electricity model. Eight neighbouring Blue Nile clusters represent **978 potential connections**, with all 8,760 hours retained. The national model supplies the local plan's actual hourly imports and their additional dispatch cost. This is a nationally supplied regional access plan, **not yet a national allocation of access technologies**.

The research question remains: **Where, and under what recovery conditions, are grid rehabilitation, mini-grids or standalone systems the least-cost way to provide reliable electricity in Sudan?** This step replaces the assumed bulk price with national dispatch, expands the local candidate graph, and checks the coupled cost bounds. Earlier sections retain the supporting evidence and previous models.
''')
    code('''import coupled_model as coupled
from check_coupled import evaluate as check_coupled
from coupled_analysis import make as coupled_figures
coupled_summary=coupled.run()
coupled_validation=check_coupled()
coupled_findings=coupled_figures()
COUPLED_OUT=coupled.OUT
coupled_sites,coupled_routes=coupled.setup()
coupled_choices=pd.read_csv(COUPLED_OUT/'settlement_choices.csv')
display(Markdown('**Completed:** three nationally coupled recovery cases, 16 independent off-grid designs, full-year service and national dispatch checks. The declared candidate graph has '+str(len(coupled_routes))+' edges.'))
''')
    md('''### 11.1 What the coupling changes

| Previous regional demonstration | This coupled study |
|---|---|
| Four clusters, 880 potential connections | Eight clusters, 978 potential connections; selected before solving |
| Assumed 0.15 USD/kWh bulk electricity | Incremental dispatch cost from the national model; no extra bulk-price charge |
| Assumed 30 kW background block | Existing national consumption and accounting losses; no duplicate synthetic background |
| Optional hypothetical 150 kW upstream repair | Existing national generation and corridors; no invented national restoration asset |
| Local feasibility and MIP gap | Local feasibility, national re-dispatch and a coupled upper/lower cost bound |

The **national fleet stays at the 2022 reference in all cases**. The scenarios change only local feeder repair budgets and outage schedules. They are not measured national war-damage cases. National generation limits, schematic transfers and annual hydro budgets are active; shortages are prohibited in these coupled solves.

The eight clusters are the nearest eligible neighbours of the previous Al Kurumuk anchor (20–500 potential connections, positive area, no detected nightlight). They share the anchor's existing 2022 weather series, with a maximum separation of 9.601 km. Their names may repeat; geohashes identify separate source clusters. Two-nearest-neighbour edges plus a geometric minimum spanning tree form the candidate graph. All route lengths are unsurveyed distance proxies.

The assigned **Roseires regional bus is an aggregate supply boundary**, not a surveyed connection from Roseires city. The 2.002 km repairable common feeder remains a hypothetical atlas-proximity proxy. Only S1 offers grid-side generation/storage. This candidate architecture does not yet model voltage, protection, detailed transformer loading, contingencies or shared mini-grids across multiple clusters.
''')
    code('''display(coupled_sites[['site_id','geohash','village_name','num_connections','distance_to_anchor_km']])
display(Image(filename=str(COUPLED_OUT/'national_coupling_map.png')))
display(pd.DataFrame([dict(scenario=k,**v) for k,v in coupled.CONFIG['scenarios'].items()]))
''')
    md('''### 11.2 Equal service, an aligned clock and no double counting

Every potential connection receives the same assumed **1 kWh/day** hourly service. Standalone and mini-grid alternatives are independently sized for all 8,760 hours; the shared grid plan must deliver the same target. The selected clusters are assumed to be **additional access demand outside the existing national total**. This is a boundary assumption, not verified evidence of their present access status.

The original national demand profile used Sudan local time; weather and local demand use UTC. A two-hour periodic shift aligns the national synthetic year to UTC while preserving annual energy. The last two UTC hours wrap to the first two local-year hours. Annual hydro energy constraints are explicitly recreated because NetCDF does not retain custom constraints.

Costs are **incremental access costs**: local systems + routes/repairs + the increase in national dispatch cost relative to its no-access baseline. The existing national operating bill and sunk national capital are not assigned to these settlements. Local costs use the same 20-year, 10% real, constant-2025-USD ledger with taxes excluded. The old national variable costs are illustrative values assigned this scenario price basis; they are not newly verified wartime prices.

These results are stationary alternatives, not sequential investments. They cannot be directly compared with section 10's total costs because coverage, background demand and upstream representation differ.
''')
    code('''display(Image(filename=str(COUPLED_OUT/'coupled_connections.png')))
display(coupled_choices.pivot(index=['site_id','source_name','connections'],columns='scenario',values='choice').reindex(columns=coupled.CONFIG['scenario_order']))
display(Image(filename=str(COUPLED_OUT/'coupled_costs_supply.png')))
display(coupled_summary[['scenario','equivalent_annual_access_cost_USD','lifecycle_access_NPC_USD','initial_local_investment_USD','incremental_national_dispatch_cost_USD','repair_spend_USD','national_import_MWh','new_route_km']].style.format(precision=2,thousands=','))
capacity_totals=coupled_choices.groupby('scenario')[['pv_kWp','diesel_kW','converter_AC_kW','battery_nominal_kWh']].sum().reindex(coupled.CONFIG['scenario_order'])
display(Markdown('**Local equipment totals:** power is in kW/kWp; battery energy is nominal kWh. These totals exclude the existing national fleet.'))
display(capacity_totals.style.format(precision=2))
display(pd.read_csv(COUPLED_OUT/'national_generation_changes_MWh.csv').set_index('scenario').style.format(precision=3))
national_facts=pd.read_csv(coupled.DATA/'national_2022.csv',index_col=0).value
sample_share=100*coupled_summary.delivered_MWh.iloc[0]/(national_facts.consumption*1000)
display(Markdown(f'**Scale:** the sample delivers {coupled_summary.delivered_MWh.iloc[0]:,.2f} MWh/year, about {sample_share:.4f}% of reference national consumer electricity. It tests a working coupling mechanism; its size is too small to establish country-wide congestion or investment needs.'))
by_recovery=coupled_summary.set_index('scenario')
cost_reduction=100*(1-by_recovery.at['broad','equivalent_annual_access_cost_USD']/by_recovery.at['constrained','equivalent_annual_access_cost_USD'])
display(Markdown(f"**What this run teaches us:** broad local recovery reduces the modelled annual access cost by {cost_reduction:.1f}% relative to constrained recovery, while delivering the same service. It selects grid service for {by_recovery.at['broad','grid_connections']:.0f} potential connections. The result reflects the combined repair-budget and outage conditions; it does not isolate the effect of budget alone. The settlement table above shows which locations retain off-grid service."))
''')
    md('''### 11.3 How the national and local models agree

The national dispatch problem gives hourly marginal costs at Roseires. These create a **supporting lower bound** on the cost of supplying any candidate import profile. The local mixed-integer model chooses its routes, primary service arrangements, repair and hub equipment against that bound. We then re-dispatch the full national network with those imports to obtain a feasible upper bound. If the bounds are too far apart, the national solution supplies another cost cut and the process repeats.

This is more than applying a fixed grid tariff: the completed plan has been supplied by an actual national re-dispatch, and the gap bounds how much a different feasible plan could improve the objective within the declared model. The lower bound uses the master's solver dual bound, including its integer gap. Completion requires the larger of **1 USD/year or 0.01%** tolerance. A negligible charging tie-break penalty is tracked separately and removed from reported resource costs.

This certificate covers the restricted graph, single-hub architecture, fixed national fleet and prescribed service. It is not proof of unrestricted national investment optimality. Numerical adequacy is also not field reliability: no uncertain outage draws or electrical protection/voltage study have been conducted.
''')
    code('''display(coupled_summary[['scenario','iterations','lower_bound_USD','feasible_upper_bound_USD','certified_absolute_gap_USD','certified_relative_gap','numerical_charge_penalty_USD']].style.format(precision=6))
display(pd.read_csv(COUPLED_OUT/'independent_checks.csv'))
display(pd.DataFrame([coupled_validation]))
numeric_reversal=(coupled_summary.lower_bound_USD-coupled_summary.feasible_upper_bound_USD).clip(lower=0).max()
display(Markdown(f'**Numerical precision:** the largest lower/upper bound reversal is {numeric_reversal:.5f} USD/year, within the documented 0.50 USD/year numerical allowance. Displayed gaps are clipped at zero; this means agreement within solver tolerance, not exact arithmetic.'))
for sc in coupled.CONFIG['scenario_order']:
    display(Markdown('**'+sc.capitalize()+' — coupling convergence**'))
    display(pd.read_csv(COUPLED_OUT/sc/'convergence.csv').style.format(precision=4))
display(Markdown('**Sample-only allocation:** '+ '; '.join(sc.capitalize()+': '+', '.join(str(count)+' connections via '+mode.replace('_',' ') for mode,count in coupled_findings['allocation'][sc].items()) for sc in coupled.CONFIG['scenario_order'])+'.'))
''')
    md('''### 11.4 What is ready and what comes next

**Ready:** joint local route/service/repair decisions, local equipment sizing, national hourly supply feasibility, annual hydro limits, aligned clocks, incremental-cost accounting, verified cached outputs and a bounded coupling solution. All source rows, assumptions and limits are explicit.

**Next implementation:** add geographically distinct settlement neighbourhoods at several national buses so they compete for national generation and corridor capacity. Then introduce national asset rehabilitation/expansion and investment periods with asset carry-over. Neither national universal-access cost nor actual damaged-asset repair priorities can be inferred by multiplying this eight-cluster result.

Measured local demand can improve the service scenarios later; it does not block this conditional modelling workflow. The most consequential remaining evidence gaps are usable tie-ins/routes, access overlap, seasonal hydro behaviour, comparable installed prices and engineering reliability. We continue with the documented public proxies rather than treating these as reasons to stop.

[Detailed formulation, assumptions and reproduction](../../docs/NATIONAL_COUPLING.md). Run `python research/system_costs/coupled_model.py` and `python research/system_costs/check_coupled.py`, or Run All here. Hash-verified results are reused offline. Changing inputs invalidates the cache. Local NetCDF files do not retain custom constraints: use the builder for a fresh solve.
''')
    return cells
