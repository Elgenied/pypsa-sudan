"""Single-notebook presentation of the uncertainty and break-even experiment."""
import nbformat as nbf

def sections():
    cells=[]
    def md(s):cells.append(nbf.v4.new_markdown_cell(s.strip()))
    def code(s):cells.append(nbf.v4.new_code_cell(s.strip()))
    md('''<a id="uncertainty-study"></a>
## 8. Uncertainty, break-even points and the next data priorities

**Which pilot choices survive changes in the assumptions—and where do they change?** This section varies ten inputs individually, then tests eight deliberately chosen joint scenarios at each cluster. Each operationally relevant problem is optimized over all 8,760 hours; identical problems reuse checked solutions. Network length/unit-price changes use exact fixed-cost adjustments where they cannot affect dispatch under this model.

These are exploratory bounds, **not observed Sudan distributions or confidence intervals**. The three clusters are illustrative, and scenario counts are not probabilities. We retain the same 2022 weather, assumed demand shape, constant-2025-USD cost basis and 20-year horizon. A result called “stable” means stable within the tests explicitly shown here.

The main deliverables are: cost-response curves, grid route thresholds, demand crossing brackets, joint-scenario cost penalties and a targeted list of evidence to collect. No current damage, verified routes or national optimum is inferred.
''')
    code('''from uncertainty_model import load_results as load_uncertainty, OUT as UOUT, DESIGN as UDESIGN
from check_uncertainty import check as check_uncertainty
from uncertainty_analysis import analyse as analyse_uncertainty, LABELS as OPTION_LABELS
from IPython.display import Image
FORCE_UNCERTAINTY_TABLES = False  # Rebuild tables; still reuse identical checked case solutions.
uncertainty, joint = load_uncertainty(force=FORCE_UNCERTAINTY_TABLES)
uncertainty_validation = check_uncertainty()
uncertainty_views = analyse_uncertainty()
display(pd.DataFrame([{'Input':k, 'Tested values':str(v['values']), 'Central':v['central'],
                      'Unit / scope':v['unit']} for k,v in UDESIGN['axes'].items()]))
display(Markdown(f"**Execution:** {uncertainty_validation['unique_hourly_cases']} distinct hourly problems, including {uncertainty_validation['fresh_solves']} new solves and reused identical baseline cases. We checked {uncertainty_validation['checked_case_hours']:,} case-hours, {len(uncertainty)} single-input option rows and {len(joint)} joint-scenario option rows. Rows are comparisons, not independent samples."))
''')
    md('''### 8.1 Demand and grid availability

Demand is scaled equally across all options at a site. Other inputs remain central in each single-input experiment. Outages begin at 18:00 local; the nine-hour schedule extends through 02:59 the next day. Longer schedules remove a nested set of hours. They are synthetic recovery stresses, not observed outage traces. Local PV/storage can be resized to supply every hour.

Points are solved cases. Lines between points aid reading and do not certify intermediate designs. Daily-demand and outage changes are separate experiments.
''')
    code("display(Image(filename=str(UOUT/'demand_outage_curves.png')))")
    md('''### 8.2 What can overturn the base-case choice?

For each tested value, compare the original base-case architecture with its cheapest competitor, after both are resized. Positive advantage means the base architecture still costs less; negative means another option becomes cheaper. Each horizontal interval shows the minimum and maximum across the selected bounds for one input, with all other inputs central.

This is a range-dependent sensitivity screen. It is not a statistical importance ranking or a formal value-of-information calculation. Grid-price and diesel-price sensitivities only affect architectures that use those supplies. The mini-grid's existing 20% annual diesel-energy cap still applies.
''')
    code('''display(Image(filename=str(UOUT/'decision_margin_ranges.png')))
priority=uncertainty_views['priorities'].copy()
priority=priority.sort_values(['geohash','base_choice_loses_at_any_tested_value','margin_range_percentage_points'],ascending=[True,False,False])
display(priority.groupby('geohash',sort=False).head(4).style.format({
    'margin_range_percentage_points':'{:.1f}','minimum_base_choice_advantage_percent':'{:.1f}',
    'maximum_base_choice_advantage_percent':'{:.1f}'}))
display(Markdown('The table identifies the most decision-sensitive tested assumptions at each cluster. Test bounds influence this order; a driver outside these bounds or an omitted interaction can still matter. Complete curves and winners are retained in `one_at_a_time.csv` and `decision_summary.csv`.'))
''')
    md(r'''### 8.3 Grid-distance break-even

Under the pilot's fixed losses and fixed usable tie-in capacity, changing new MV length changes only infrastructure cost:

$$C_\mathrm{grid}(L)=C_\mathrm{grid}(0)+a_\mathrm{MV}L,\qquad L^*=\frac{C_\mathrm{best\ offgrid}-C_\mathrm{grid}(0)}{a_\mathrm{MV}}.$$

The coefficient includes the full annualized line cost from the lifecycle ledger. The crossing is exact **within that simplified model**. A blank threshold means grid already costs more than the cheapest off-grid alternative at zero new MV length. The axes show hypothetical **route kilometres**, not straight-line distance; actual routes, losses, voltage and upstream capacity remain unverified. Each site keeps its own LV layout and demand.
''')
    code('''display(Image(filename=str(UOUT/'route_break_even.png')))
route_thresholds=pd.read_csv(UOUT/'route_thresholds.csv')
display(route_thresholds[['source_name','geohash','outage_hours','best_offgrid','assumed_route_km',
                          'break_even_new_MV_route_km','status']].style.format({
                          'assumed_route_km':'{:.2f}','break_even_new_MV_route_km':'{:.2f}'},na_rep='No nonnegative crossing'))
''')
    md('''### 8.4 Demand and outage crossing brackets

Demand thresholds compare **mini-grid versus standalone**, with all other assumptions central. Each observed sign change is refined with full-year optimization to a bracket at most 0.025 kWh per service point per day wide. This pairwise crossing does not establish that either option beats grid supply. “No sign change” refers only to the tested demand grid; no global uniqueness claim is made.

Outage brackets use the tested 0, 3, 6 and 9-hour schedules. We do not interpolate a precise fractional-hour reliability threshold from these points.
''')
    code('''demand_thresholds=pd.read_csv(UOUT/'demand_thresholds.csv')
outage_thresholds=pd.read_csv(UOUT/'outage_threshold_brackets.csv')
display(Image(filename=str(UOUT/'demand_break_even.png')))
display(demand_thresholds.style.format({'lower_kWh_day':'{:.3f}','upper_kWh_day':'{:.3f}',
      'lower_mini_minus_standalone_USD_kWh':'{:.4f}','upper_mini_minus_standalone_USD_kWh':'{:.4f}'}))
display(outage_thresholds)
''')
    md('''### 8.5 Combined assumptions: stable choices and close alternatives

Eight corners combine daily demand (0.5 or 2 kWh/service point), lower/higher PV-and-battery equipment costs, and grid availability (0 or 6 hours of evening interruption). All other inputs remain central. Paired hardware costs are a deliberate bundle, not a measured correlation. Finance and fuel interactions are not covered by this joint design.

Each cell below shows the cost premium over the cheapest architecture in that scenario. All capacities are chosen again in each scenario: **this is an adaptive-capacity architecture comparison, not the regret of building one fixed system before uncertainty is revealed**. A fixed-design robustness study would require a different experiment.
''')
    code('''display(Image(filename=str(UOUT/'joint_scenario_regret.png')))
robustness=uncertainty_views['robustness']
display(robustness[['source_name','mode','scenarios','strictly_cheapest_count','within_5_percent_count',
                    'min_USD_kWh','max_USD_kWh','max_adaptive_capacity_regret_percent']].style.format({
                    'min_USD_kWh':'{:.3f}','max_USD_kWh':'{:.3f}','max_adaptive_capacity_regret_percent':'{:.1f}'}))
display(Markdown('**Interpretation:** “6 of 8 cases” is a scenario count, not a 75% probability. “Within 5%” is an explicitly chosen near-tie criterion. Min/max costs are ranges over these scenarios, not confidence intervals.'))
''')
    md('''### 8.6 Findings generated from this run
''')
    code('''findings=[]
for sid,g in robustness.groupby('geohash',sort=False):
    text=', '.join(f"{OPTION_LABELS[r['mode']]} cheapest in {int(r.strictly_cheapest_count)}/8 cases" for _,r in g.iterrows())
    findings.append(f"- **{g.source_name.iloc[0]} [{sid}]:** {text}.")
for r in demand_thresholds.query("status=='sign_change_bracket'").itertuples(index=False):
    findings.append(f"- **Demand crossing, {r.source_name}:** mini-grid and standalone exchange cost order between **{r.lower_kWh_day:.3f} and {r.upper_kWh_day:.3f} kWh/service point/day**, conditional on central prices and the assumed load shape.")
near_id=sites.query("pilot_type=='near_grid'").iloc[0].geohash
nr=route_thresholds[(route_thresholds.geohash==near_id)&(route_thresholds.outage_hours==0)].iloc[0]
if pd.notna(nr.break_even_new_MV_route_km):
    findings.append(f"- **Near-grid route threshold:** with continuous upstream service, the grid/off-grid crossing is **{nr.break_even_new_MV_route_km:.2f} route km**, compared with a current unsurveyed proxy of **{nr.assumed_route_km:.2f} km**.")
display(Markdown('\\n'.join(findings)))
''')
    md('''### 8.7 What evidence to collect next

Use the sensitivity results to target validation:

1. **Demand:** verify service points and household/business/clinic loads, particularly near the demand crossing brackets. A building count and a repeated evening profile remain proxies.
2. **Grid feasibility and reliability:** establish a usable tie-in, its capacity and outage record, and a buildable route. Compare route evidence against the conditional thresholds rather than atlas proximity alone.
3. **Comparable procurement:** obtain mini-grid and standalone quotations with the same service, equipment, delivery, installation and replacement scope. Test the standalone purchasing premium explicitly.
4. **Storage and finance:** validate battery lifetime, temperature exposure, replacement access and financing terms. Battery price was varied here; its lifetime remains eight years.

Then test selected fixed designs against multiple weather years, demand shapes and unplanned equipment/fuel outages, and expand to a justified settlement sample. Shared feeder decisions and upstream constraints are required before interpreting a settlement map as a national least-cost plan.

**What is checked:** complete hourly inputs; equal service; AC and chronological battery balances; operating/capacity/SOC limits; outage and fuel restrictions; reconstructed capital and lifecycle costs; monotonicity under tighter supply or higher costs; and threshold arithmetic. Passing these checks does not validate the field assumptions.
''')
    code('''display(pd.DataFrame([uncertainty_validation]))
display(Markdown('Experiment inputs and interpretation: [uncertainty input guide](../../data/electrification_uncertainty/README.md). Complete outputs: `results/uncertainty/`. Run `python research/system_costs/uncertainty_model.py` and `python research/system_costs/check_uncertainty.py` from the project root. Normal reading/rerunning uses verified cached solutions; input changes trigger re-optimization.'))
''')
    return cells
