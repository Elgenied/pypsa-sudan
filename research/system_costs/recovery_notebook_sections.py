"""Question-led joint planning section in the existing reader-facing notebook."""
import nbformat as nbf

def sections():
    cells=[]
    def md(s):cells.append(nbf.v4.new_markdown_cell(s.strip()))
    def code(s):cells.append(nbf.v4.new_code_cell(s.strip()))
    md('''<a id="recovery-planning"></a>
## 10. Joint recovery planning: where should we repair, connect or supply locally?

**Research question:** Where, and under what recovery conditions, are grid rehabilitation, mini-grids or standalone systems the least-cost way to provide reliable electricity in Sudan?

This section implements the first **joint regional demonstration**: four neighbouring Blue Nile clusters, 880 potential connections, a common repairable feeder, alternative shared new routes, limited regional supply and a separate existing-load block. It optimizes discrete service/repair/route choices together with hourly grid-connected equipment sizing and operation. It does not allocate technology across Sudan yet.

**Read this section first for the current study.** Earlier sections retain the source evidence, accounting and supporting sensitivity work. We hold demand and prices fixed and compare only three coherent recovery conditions.
''')
    code('''import importlib
import recovery_model as recovery
importlib.reload(recovery)
from recovery_analysis import make as recovery_figures
from check_recovery import evaluate as check_recovery
from IPython.display import Image
recovery_summary=recovery.run()
recovery_validation=check_recovery()
recovery_findings=recovery_figures()
RECOVERY_OUT=recovery.OUT
recovery_sites=pd.read_csv(recovery.DATA/'sites.csv')
recovery_choices=pd.read_csv(RECOVERY_OUT/'settlement_choices.csv')
display(Markdown('**Completed:** three joint 8,760-hour optimizations, plus eight independently optimized off-grid designs. All saved decisions, hourly balances, lifecycle costs and repair budgets are checked below.'))
''')
    md('''### 10.1 What is observed, what is assumed, and what the model decides

| Available input | Use in this model | Limit |
|---|---|---|
| Atlas cluster coordinates, buildings, area and line proximity | Existing Al Kurumuk pilot plus its three nearest eligible neighbours; network length proxies and 880 potential service points | Buildings are not verified customer accounts; nightlight absence is not proof of no connection |
| Existing NASA POWER 2022 hourly series at Al Kurumuk | Shared solar/weather input across sites within 2.21 km | Horizontal-array approximation; no claim of four independent weather observations |
| Full system-cost ledger | Equipment, connections, networks, repair, O&M and replacements | Provisional constant-2025 USD inputs; taxes excluded from this resource-cost comparison |
| Existing 2022 national model | Historical study context | **Not dynamically coupled** to this demonstration; regional supply is an aggregate limited interface |

The common feeder is **hypothetical repairable infrastructure**, with a 2.002 km length proxy (1.54 km atlas proximity ×1.3). Its repair cost is 35% of the new-line component cost, plus the ledger's applicable project allowances. The upstream repair restores a separate 150 kW supply block. Neither is an observed damage record. Source conflict categories are not used as damage estimates.

We prescribe **1 kWh per potential connection per day**, the same evening-heavy hourly service profile for every option, and a separate assumed existing-load block with 30 kW peak. The latter excludes the four clusters by construction; it is not estimated total Blue Nile demand. Regional bulk supply has a finite capacity and an explicit cost. A dedicated, costed backup generator can serve the existing-load block, but cannot supply the settlement feeder.

The model chooses one primary arrangement per cluster, which routes to build, whether to repair the common feeder and upstream block, and the grid-connected PV, battery, converter and diesel capacities. **For this first demonstration, grid-side generation/storage is offered at one shared hub at S1**, supplying connected sites through selected routes. Selecting the common feeder also connects S1. Grid-side equipment at every settlement is not offered: the result is least cost within this restricted architecture set, not an unrestricted regional optimum. Standalone designs represent identical separate service-point systems with no load-diversity benefit; mini-grids have local distribution. All satisfy identical delivered service.
''')
    code('''display(recovery_sites[['site_id','geohash','village_name','num_connections','hull_area','distance_to_anchor_km']])
recovery_conditions=pd.DataFrame([dict(scenario=k,**v) for k,v in recovery.CONFIG['scenarios'].items()])
display(recovery_conditions[['label','repair_budget_USD','existing_supply_MW','outage_local_hours']])
''')
    md('''### 10.2 Three recovery conditions, one service standard

The repair budgets are **regional demonstration allowances**, not Sudan reconstruction budgets. Only the initial repair expenditures count against them; new local generation and new feeder investment are minimized but not capped by that repair budget. Increasing available upstream supply and reducing outage hours describe exogenous recovery outside this boundary; their external restoration expenditure is not estimated. Therefore cross-scenario cost reductions are conditional outcomes, **not a benefit-cost appraisal of national recovery**.

All three cases have the same demand, prices, 20-year horizon and real 10% discount rate. They are alternative stationary recovered-system conditions, not a dated transition pathway. Each case must meet every modelled hour, without load shedding. Diesel for settlement systems is limited to 20% of annual delivered energy; this is a declared planning constraint, not a reliability law. Network transfer limits and constant losses are represented; voltage, protection and contingency studies are not.

**Objective:** minimize equivalent annual lifecycle resource costs (equivalent to NPC for this common horizon), including fixed service activation, shared routes once, repairs, local equipment and actual hourly fuel/bulk energy. Sunk original grid construction is excluded.

Standalone and mini-grid capacity designs are first optimized independently for each cluster. Their minimized costs enter the joint model as binary, exact-service options. This decomposition is exact within the formulation because these options have no inter-settlement exchanges or shared fuel/investment constraint. Grid equipment and dispatch remain jointly optimized. Connectivity constraints prevent a grid-labelled island; binary route activation prevents fractional feeder construction. Every hour of 2022 is retained, with chronological cyclic storage and no representative-day compression.
''')
    code('''display(Image(filename=str(RECOVERY_OUT/'recovery_choices_map.png')))
display(Image(filename=str(RECOVERY_OUT/'recovery_connections.png')))
display(recovery_choices.pivot(index=['site_id','source_name','connections'],columns='scenario',values='choice').reindex(columns=recovery.CONFIG['scenario_order']))
''')
    md('''**Reading the saved results:** With no repair budget, Kubbaka (S3) uses a mini-grid and the other clusters use standalone systems. Partial recovery makes a shared grid connection to Al Kurumuk (S1) and Kubbaka (S3) economical; the two smaller clusters remain standalone. Broad recovery connects all four through S1–S2, S2–S3 and S2–S4, and selects both candidate repairs.

These are separate stationary plans, not a recommendation to install and then discard the off-grid systems in that order. A transition study must explicitly carry existing investments between periods. Under the broad case's assumed continuous upstream availability, the optimizer chooses about 50.9 kWp of hub PV and no settlement storage or diesel. That result depends on the stated availability; it does not establish real-world outage resilience.
''')
    md('''### 10.3 Investment, shared infrastructure and operation

The mapped edges are straight-line ×1.3 candidate new routes between source coordinates. All six pairwise candidates are offered; the solver pays a route's fixed lifecycle cost once, regardless of how many downstream settlements use it. The assumed common feeder reaches S1; its actual geographic path is unknown and is not drawn as if surveyed.

The allocation pies show **potential connections**, not population, energy shares or state-wide coverage. Equipment capacities are separated into power (kW/kWp) and battery energy (kWh). Total costs include the separate existing-load block; they must not be divided solely by settlement energy and labelled a settlement LCOE.
''')
    code('''display(Image(filename=str(RECOVERY_OUT/'recovery_costs_capacities.png')))
display(recovery_summary[['scenario','equivalent_annual_cost_USD','lifecycle_NPC_USD','initial_investment_USD','repair_spend_USD','new_feeder_km','repaired_common_feeder_km','restored_upstream_MW']].style.format(precision=2,thousands=','))
display(recovery_choices[['scenario','site_id','choice','pv_kWp','battery_nominal_kWh','converter_AC_kW','diesel_kW']].style.format(precision=2))
for sc in recovery.CONFIG['scenario_order']:
    display(Markdown('**'+recovery.CONFIG['scenarios'][sc]['label']+' — selected repairs/routes**'))
    repairs=pd.read_csv(RECOVERY_OUT/sc/'repair_asset.csv')
    routes=pd.read_csv(RECOVERY_OUT/sc/'route_build.csv')
    display(repairs);display(routes)
''')
    md('''### 10.4 What has been checked and what this answers

Independent checks reload the exported PyPSA networks and custom decisions, then reconstruct all bus balances, full-year battery chronology, capacity limits, option activation, equal service, diesel limits, connected grid paths, repair budgets, and lifecycle costs. They also check the no-repair-budget limiting case and the nested recovery feasible sets. The solver's achieved mixed-integer optimality gap is reported; the target tolerance is 0.01%. Numerical validation is not field validation.

The answer is now **a jointly optimized local recovery plan conditional on a declared candidate network and a single grid-side backup hub**. The preferred choices may change with recovery because settlements can share routes and draw on restored supply. The model is not forced to select all three technologies. A technology winning nowhere in a case is a valid result.

The next implementation step is geographic scaling: repeat and connect regional candidate graphs, replace the assumed feeder with source-traced infrastructure where possible, and couple aggregate supply to the national generation/transmission model. Measured demand is not a prerequisite for extending the conditional model. National allocation, observed damage-based rehabilitation, engineering reliability and investment sequencing remain outside the present result.

**Reproduce:** run `python research/system_costs/recovery_model.py` and `python research/system_costs/check_recovery.py`, or Run All in this notebook. Cached results are verified against input and output hashes. `--force` re-solves. Model files (`network.nc`) omit custom constraints; rerun the Python builder to recreate them. Separate decision CSVs retain all service, route, repair and connectivity variables. See [method and scope](../../docs/RECOVERY_MODEL.md).
''')
    code('''display(pd.read_csv(RECOVERY_OUT/'independent_checks.csv'))
display(pd.DataFrame([recovery_validation]))
display(Markdown('**Sample-only finding:** '+ '; '.join(recovery.CONFIG['scenarios'][sc]['label']+': '+', '.join(f'{count} connections via {mode.replace("_"," ")}' for mode,count in recovery_findings['allocation'][sc].items()) for sc in recovery.CONFIG['scenario_order'])+'.'))
''')
    return cells
