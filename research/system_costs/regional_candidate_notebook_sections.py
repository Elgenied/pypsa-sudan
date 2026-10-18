"""Reader-facing candidate robustness experiment in the single study notebook."""
import nbformat as nbf

def sections():
    cells=[]
    def md(s):cells.append(nbf.v4.new_markdown_cell(s.strip()))
    def code(s):cells.append(nbf.v4.new_code_cell(s.strip()))
    md('''<a id="candidate-diagnostic"></a>
## 13. Do the surprising regional switches survive broader candidate designs?

**Read this after section 12 before citing the regional technology map.** Section 12 records the original scenario-specific library. This section keeps every original candidate and allows additional physically feasible grid designs. It diagnoses model structure, not new field evidence.

In the original model, each zone had one grid design per recovery condition, pre-sized at 140 USD/MWh. An outage-free design can remove batteries and rely more heavily on national imports. A better recovery scenario therefore replaced, rather than retained, an earlier grid-plus-storage option. That is not a nested investment choice set.

**Controlled experiment:** keep the same 36 zones, hourly demand, 2022 weather, costs, national fleet, hydro budgets, four repair projects and recovery constraints. Selective recovery can choose its original grid design or the restricted-recovery grid design (72 grid candidates). Restored recovery can choose any of the three grid designs (108 grid candidates). Both retain the same 72 mini-grid/standalone candidates. Earlier schedules remain feasible because their outage hours include the receiving scenario's outage hours; this is checked hour by hour. Equipment and dispatch remain fixed inside each candidate. The optimizer chooses at most one grid design per zone, or the cheaper independent off-grid option.

The fixed-choice restored baseline is replayed with a new multi-candidate formulation first. A further counterfactual requires all six Gezira zones to use a grid portfolio, while allowing other zones and national dispatch to adjust. This quantifies a modelled system-cost penalty, not a household tariff.
''')
    code('''from pathlib import Path
import json
import pandas as pd
from IPython.display import display, Markdown, Image
here=Path.cwd().resolve()
project=next(p for p in [here,*here.parents] if (p/'data/regional_model/config.json').exists())
CANDIDATE_OUT=project/'research/system_costs/results/regional_candidate_diagnostic'
REBUILD_CANDIDATE_STUDY=False  # Set True to solve/reuse checked caches, validate, and redraw.
if REBUILD_CANDIDATE_STUDY:
    import regional_candidate_diagnostic as diagnostic
    from check_regional_candidates import check
    from regional_candidate_analysis import make
    diagnostic.solve('restored',False,fixed=True)
    diagnostic.solve('selective')
    diagnostic.solve('restored')
    diagnostic.solve('restored',force_gezira=True)
    check()
    make()
validation=json.loads((CANDIDATE_OUT/'validation.json').read_text())
assert validation['passed']
findings=json.loads((CANDIDATE_OUT/'findings.json').read_text())
comparison=pd.read_csv(CANDIDATE_OUT/'comparison.csv')
display(Markdown(f"**Verification passed:** {len(validation['cases'])} full-year cases, {validation['local_library_designs_checked']} existing local designs checked; no load-shedding generator. These are numerical checks, not field validation."))
display(comparison.style.format(precision=2,thousands=','))
for scenario in ['selective','restored']:
    f=findings[scenario]
    display(Markdown(f"**{scenario.capitalize()} recovery:** annual cost changes by **{f['cost_change_percent']:.2f}%**; {f['changed_zones']} zones change primary service mode, covering {f['changed_connections_percent']:.1f}% of potential building connections. Gezira's grid-labelled connections change from {f['gezira_grid_original']:,} to {f['gezira_grid_expanded']:,}."))
    display(Markdown(f"The solver-bound interval for annual cost reduction is **{f['minimum_cost_reduction_USD']:,.0f}–{f['maximum_cost_reduction_USD']:,.0f} USD/year**."))
if findings['restored']['gezira_grid_original']==0 and findings['restored']['gezira_grid_expanded']>0:
    display(Markdown('**Scientific conclusion:** the original all-standalone Gezira result does not survive retaining additional feasible grid designs. It is sensitive to candidate construction and should not be presented as a robust regional recommendation. The expanded result remains conditional on the same spatial, demand, weather and cost assumptions.'))
else:
    display(Markdown('**Scientific conclusion:** inspect the reported zone changes; persistence of a choice only establishes robustness to this specified library expansion, not to unrestricted joint equipment sizing.'))
display(Image(filename=str(CANDIDATE_OUT/'candidate_costs_and_gezira.png')))
''')
    md('''### 13.1 Before/after maps and design mechanism

The points inherit whole-zone choices, not independently optimized settlement decisions. Blue means grid with possible local PV/battery support; it does not mean all energy comes from the grid. The total system cost includes national background operation and should not be presented as a new-access investment budget.
''')
    code('''display(Image(filename=str(CANDIDATE_OUT/'candidate_choices_map.png')))
display(Markdown('**Gezira grid designs, aggregated across its six zones:** compare the batteries retained and annual imports required by each design family. These are alternative candidates, not three simultaneous investments.'))
display(pd.read_csv(CANDIDATE_OUT/'gezira_grid_design_totals.csv').style.format(precision=1,thousands=','))
choices=pd.read_csv(CANDIDATE_OUT/'all_zone_choices.csv')
display(choices.query("library == 'Expanded' and state == 'Gezira'")[['scenario','zone_id','mode','design_scenario','pv_kWp','battery_nominal_kWh','grid_import_MWh','local_EAC_USD']].style.format(precision=1,thousands=','))
''')
    md('''### 13.2 Does requiring grid service in Gezira impose a cost?

The counterfactual retains the expanded restored-recovery library and requires grid service in every Gezira zone. Compare the full reoptimized system with the unrestricted expanded case. The interval uses each mixed-integer solve's incumbent and lower bound. Small differences within that interval are not evidence of a precise preference. A fixed-choice LP reproduction establishes formulation consistency, not global optimality of the original plan.
''')
    code('''f=findings['force_all_gezira_grid']
display(Markdown(f"Requiring all Gezira zones to use grid service changes the incumbent annual system cost by **{f['additional_annual_cost_USD']:,.0f} USD/year**. The solver-bound interval for the minimum added cost is **{f['minimum_regret_USD']:,.0f}–{f['maximum_regret_USD']:,.0f} USD/year**."))
display(pd.DataFrame(validation['cases']))
''')
    md('''### 13.3 What this establishes—and what remains open

If a switch disappears after feasible designs are retained, the original map was sensitive to candidate construction and should not be cited as a robust geographic recommendation. If it persists, it survives this specific expansion; it is not proven robust to all designs or assumptions.

This experiment expands the set of feasible **grid PV/battery portfolios**, using already optimized hourly schedules. It does not add new technologies, optimize local dispatch against endogenous national hourly prices, or allow continuous joint equipment sizing. Mini-grid and standalone designs are unchanged. Whole-zone decisions, proxy routes, synthetic demand, hypothetical damage/repair costs and one weather year remain limitations. In particular, this experiment alone cannot prove that grid-led alternatives in the earlier policy benchmarks are universally infeasible.

Reproduce from the repository root:
```bash
python research/system_costs/regional_candidate_diagnostic.py
python research/system_costs/check_regional_candidates.py
python research/system_costs/regional_candidate_analysis.py
```
Saved inputs and outputs are hash-checked per case. The original section-12 results remain available for an auditable before/after comparison.
''')
    return cells
