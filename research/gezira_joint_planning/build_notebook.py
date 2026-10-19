"""Build and execute the standalone section-14 reader notebook."""
from pathlib import Path
import argparse,nbformat as nbf
from nbclient import NotebookClient
from nbconvert import HTMLExporter
ROOT=Path(__file__).resolve().parent

def build():
    cells=[]
    def md(s):cells.append(nbf.v4.new_markdown_cell(s.strip()))
    def code(s):cells.append(nbf.v4.new_code_cell(s.strip()))
    md('''# 14. Gezira: joint grid, solar and battery planning

**A separate notebook continuing the PyPSA-Sudan regional study.** Read the [section-13 comparison](../system_costs/Sudan_System_Costs.html#candidate-diagnostic) for the earlier experiment. This notebook asks whether its Gezira choices survive allowing solar capacity, battery energy, converter power and hourly grid imports to be optimized jointly with national generation and transfers.

The study uses the same six Gezira planning zones, the same atlas clusters and potential building connections, the same demand targets and synthetic hourly shapes, the same 2022 zone weather and the same lifecycle cost assumptions. Potential connections are not observed household accounts. This is a conditional planning experiment, not a measured reconstruction of war damage or an implementation-ready connection map.

**Controlled boundary:** the other 30 regional zones keep their section-13 service designs and hourly imports. Backbone repairs also stay at that scenario's section-13 selection. National generation and corridor flows are redispatched across all 8,760 hours. Therefore the result is a Gezira planning improvement conditional on the surrounding system, not a newly optimized six-state or national investment plan.
''')
    code('''from pathlib import Path
import sys,json
import pandas as pd
from IPython.display import display,Markdown,Image
here=Path.cwd().resolve()
PROJECT=next(p for p in [here,*here.parents] if (p/'data/regional_model/config.json').exists())
STUDY=PROJECT/'research/gezira_joint_planning'
sys.path.insert(0,str(STUDY))
import model
RESULTS=STUDY/'results'
REBUILD=False  # Set True to solve/reuse hash-checked cases and regenerate checks/figures.
if REBUILD:
    for scenario in ['selective','restored']:
        model.solve(scenario,False)
        model.solve(scenario,True)
    from check import check
    from analysis import make
    check();make()
validation=json.loads((RESULTS/'validation.json').read_text())
assert validation['passed']
for scenario in ['selective','restored']:
    for free in [False,True]:
        case=scenario+('_joint_choices' if free else '_fixed_choices')
        manifest=json.loads((RESULTS/case/'manifest.json').read_text())
        assert manifest['inputs']==model.fingerprint(scenario,free), 'Saved model inputs have changed; rebuild first.'
        assert all(model.lib.r.sha(RESULTS/case/f)==h for f,h in manifest['outputs'].items()), 'Saved case outputs changed.'
comparison=pd.read_csv(RESULTS/'comparison.csv')
choices=pd.read_csv(RESULTS/'all_choices.csv')
findings=json.loads((RESULTS/'findings.json').read_text())
display(Markdown(f"**Completed and checked:** {len(validation['cases'])} new full-year cases, six Gezira zones, 8,760 chronological hours each. No load-shedding generator is allowed."))
for scenario,f in findings.items():
    display(Markdown(f"**{scenario.capitalize()}:** full-system annual cost changes from **{f['original_cost_USD']/1e9:.3f} to {f['joint_cost_USD']/1e9:.3f} billion USD** ({f['saving_percent']:.2f}% reduction). Gezira's grid-labelled potential connections change from **{f['grid_share_original_percent']:.1f}% to {f['grid_share_joint_percent']:.1f}%**; {f['changed_zones']} zones change service mode."))
''')
    md('''## 14.1 What changes between the three stages?

| Stage | Gezira service choices | Grid-connected equipment and operation | Other zones / backbone repairs |
|---|---|---|---|
| Section 13 | Saved choices among fixed portfolios | Pre-sized capacities and fixed hourly import schedules | Saved section-13 plan |
| Resize only | Fixed to section 13 | PV, battery energy, converter power and hourly imports optimized jointly | Fixed to the same saved plan |
| Resize + choose | Grid versus independently optimized mini-grid/standalone allowed to change | Same joint optimization for grid portfolios | Fixed to the same saved plan |

We run **selective** and **restored** recovery. Selective grid imports are unavailable during local hours 19–21; restored has no scheduled local outage. The national supply limits still apply in every hour. The restricted case is not rerun here. Each recovery scenario retains its own surrounding grid demand and repair plan. Compare the three stages within a scenario to isolate the value of Gezira flexibility; differences between recovery scenarios also reflect those surrounding conditions.

Mini-grid and standalone supply retain their independently optimized hourly designs. They do not trade with other zones and have no shared fuel/land/budget constraint in this experiment. Eliminating the more expensive of those two independent options preserves their least-cost comparison under the same scaling assumptions. This does not introduce new off-grid technologies or model productive demand.

The objective includes the complete annualized local equipment and network costs, replacements and maintenance; actual national generation operating cost; and the fixed outside-region portfolio and backbone-repair costs. **These totals include national background operation. They are not new-electrification investment budgets.** Grid imports are not charged twice at the illustrative sizing price used in earlier sections. A very small charging tie-break is removed from reported resource costs.
''')
    code('''display(Image(filename=str(RESULTS/'joint_comparison.png')))
display(pd.DataFrame(findings).T[['resizing_saving_USD','additional_service_choice_saving_USD','gezira_local_cost_reduction_USD','national_operating_cost_increase_USD']].style.format(precision=0,thousands=','))
display(Markdown('Savings split into resizing with fixed service choices and the additional value of changing service choices. The local cost reduction minus the increase in national operating costs equals the total saving; other-zone and backbone-repair costs are fixed.'))
display(comparison[['scenario','stage','annual_system_cost_USD','annual_cost_saving_USD','gezira_local_annual_cost_USD','grid_share_percent','grid_import_MWh','pv_MW','battery_MWh','mip_gap']].style.format(precision=2,thousands=','))
''')
    md('''## 14.2 Where do choices change?

Each source point inherits the choice for its planning zone. Six zones are not six physical microgrids: local equipment represents proportionally replicated cluster systems under a shared demand and weather shape. There are no modelled electrical transfers between separate settlements within a zone. Grid connection routes remain cost proxies, not surveyed routes. Blue indicates grid service **with possible local solar and batteries**, not exclusively grid-supplied energy.
''')
    code('''display(Image(filename=str(RESULTS/'gezira_choices_map.png')))
display(choices[['scenario','stage','zone_id','mode','connections','target_MWh','pv_kWp','battery_nominal_kWh','converter_AC_kW','grid_import_MWh','local_annual_cost_USD']].style.format(precision=1,thousands=','))
''')
    md('''## 14.3 How the hourly physical model works

Each grid-selected zone has an AC service bus, a solar generator, a battery energy store and a shared bidirectional converter. Import links connect the local service to Wad Medani; reverse exports are not allowed. The load includes the same 10% local grid-distribution loss as the earlier portfolios. Battery charge and discharge efficiencies are 95%, usable state of charge is 10–90%, and the year is cyclic. Converter charging and discharging share one AC power rating and one investment cost.

Capacity limits preserve the normalized design limits from section 13, scaled by annual zone service; they are not new per-household surveys. A binary grid choice activates grid infrastructure, solar, battery, converter and import capacities. When off-grid is chosen, those capacities are zero and the independently feasible off-grid schedule supplies the same delivered demand. Any load-cancellation variable is bookkeeping only and is excluded from physical generation.

The import ceiling and distribution/transformer quantities retain section 13's screening assumptions. This model does not resize real feeders or transformers to the optimized charging peak, so additional engineering checks would be required before interpreting a grid portfolio as buildable.

National hydro retains its annual and historical-shape monthly energy limits. Schematic transmission capacities reflect the saved repairs. There is no reservoir inflow model, distribution voltage analysis or added national generation investment.
''')
    code('''display(Image(filename=str(RESULTS/'annual_supply_mix.png')))
for scenario,f in findings.items():
    display(Markdown(f"**{scenario.capitalize()} physical design:** {f['joint_pv_MW']:.1f} MW local solar and {f['joint_battery_MWh']:.1f} MWh nominal battery capacity. National imports provide {f['national_import_share_of_local_supply_percent']:.1f}% of annual primary electricity entering the local systems. This import share is different from the fraction of connections assigned grid service."))
display(Image(filename=str(RESULTS/'hourly_operation.png')))
hourly=pd.read_csv(RESULTS/'hourly_gezira.csv.gz')
display(hourly.groupby('scenario')[['target_delivered_MW','pv_MW','diesel_MW','grid_MW','charge_MW','discharge_MW']].sum().rename(columns=lambda c:c.replace('_MW','_MWh')).style.format(precision=0,thousands=','))
display(Markdown('Hourly outputs include both selected grid and selected off-grid systems. Battery discharge is stored energy, not an additional primary generation source; PV/grid supply also cover distribution and storage losses.'))
''')
    md('''## 14.4 Numerical validation and interpretation

The independent checker reloads saved networks, reconstructs national and local electricity balances, verifies cyclic battery energy and capacity limits, checks outages, import limits and shared converter ratings, and recomputes equipment costs through the lifecycle ledger. It checks the fixed other-zone demands and repaired corridor capacities against section 13. The selected off-grid designs retain their saved service schedules. No unmet-load generator is permitted.

The original section-13 design remains feasible in the resize-only formulation, so an increase in minimized cost beyond numerical tolerances would flag a problem. The freely selected service formulation also retains every resize-only solution. Mixed-integer gaps refer to the total objective including fixed system costs; they do not establish a precise local willingness-to-pay. Savings below are relative to the **saved reference plan**, with the other zones and repairs held fixed, not to a proven unrestricted regional optimum.
''')
    code('''display(pd.DataFrame(validation['cases']).style.format(precision=8))
for scenario,f in findings.items():
    display(Markdown(f"**{scenario.capitalize()} savings versus the saved section-13 plan:** the solver-bound resource-cost interval is **{f['minimum_saving_vs_saved_reference_USD']/1e6:.3f}–{f['maximum_saving_vs_saved_reference_USD']/1e6:.3f} million USD/year**. This interval accounts conservatively for the numerical cycling tie-break."))
''')
    md('''## 14.5 What this step can support

A changed service choice shows that independent grid sizing at a fixed bulk price was insufficient to establish a robust geographic preference. An unchanged choice survives this specific joint-sizing test; it is not validated against every possible demand profile, weather year, route or damage condition. Review cost and capacity changes alongside service shares: an unchanged label can hide a substantially different physical system.

The next extension is to let all regional zones resize together and reconsider backbone repairs in the same optimization. That is a separate experiment: this notebook intentionally holds the surrounding plan fixed to identify the value of Gezira flexibility. Before publication, additional weather/hydro years, independent evidence checks and suitably bounded claims remain important. The absence of measured hourly demand does not prevent transparent scenario research, but results must not be described as observed electricity access or field-validated construction recommendations.

**Solver provenance:** three cases use HiGHS 1.12.0; the restored joint-choice case uses Gurobi 13.0.1 because HiGHS was slow at its root relaxation. The formulation is unchanged. Rebuilding that case with the default solver requires Gurobi and a license; `model.py --solver highs` uses the open-source alternative for all cases, with potentially longer runtime. Valid cached cases are reused; move a case directory aside to force a fresh solve. Reading this notebook and validating the saved outputs require no Gurobi license. CI performs those saved-output checks and notebook execution, not full optimization reruns.

**Reproduce from the repository root using the `pypsa` conda environment:**
```powershell
python research/gezira_joint_planning/model.py
python research/gezira_joint_planning/check.py
python research/gezira_joint_planning/analysis.py
python research/gezira_joint_planning/build_notebook.py --execute
```

Sources, costs and recovery assumptions are inherited from [the regional model documentation](../../docs/REGIONAL_MODEL.md), [system-cost inputs](../../data/system_costs/README.md), and the cached data in `data/regional_model/`. No new observational data are introduced here. Saved cases contain source/output fingerprints, solver logs, NetCDF networks, choices and cost summaries. Reconstruct custom constraints with `model.py`; the NetCDF file alone does not preserve those constraints.
''')
    nb=nbf.v4.new_notebook(cells=cells,metadata={'kernelspec':{'display_name':'Python (pypsa)','language':'python','name':'pypsa'}})
    return nb

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--execute',action='store_true');p.add_argument('--kernel',default='pypsa');a=p.parse_args()
    nb=build()
    if a.execute:NotebookClient(nb,timeout=600,kernel_name=a.kernel,resources={'metadata':{'path':str(ROOT)}}).execute()
    nbf.write(nb,ROOT/'Sudan_Gezira_Joint_Planning.ipynb')
    if a.execute:
        exporter=HTMLExporter(template_name='lab');exporter.exclude_input=True
        body,_=exporter.from_notebook_node(nb);(ROOT/'Sudan_Gezira_Joint_Planning.html').write_text(body,encoding='utf-8')
    print('Executed' if a.execute else 'Built',ROOT/'Sudan_Gezira_Joint_Planning.ipynb')
