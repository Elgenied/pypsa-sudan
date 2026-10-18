"""Build the single reader-facing cost notebook. Inputs remain editable CSVs."""
from pathlib import Path
import nbformat as nbf
ROOT=Path(__file__).resolve().parent
cells=[]
def md(text): cells.append(nbf.v4.new_markdown_cell(text.strip()))
def code(text): cells.append(nbf.v4.new_code_cell(text.strip()))

md('''# PyPSA-Sudan: least-cost electrification under recovery conditions

**Start with [section 12: six-state regional study](#regional-study)** for all 11,268 atlas clusters in Northern, River Nile, Khartoum, Gezira, White Nile and Sennar, grouped into 36 planning zones. Regional service portfolios and backbone repair scenarios are linked to national hourly dispatch. Supporting work: [Eight-cluster coupling](#national-coupling) · [Four-cluster demonstration](#recovery-planning) · [Hourly pilot](#optimized-pilot) · [Uncertainty and break-even](#uncertainty-study) · [18-state sample](#spatial-proxy-study).

This notebook assembles equipment, installed networks, connections, delivery, installation, project development, tax allowances, annual operation, replacements, disposal and finance. It is the cost layer for the post-war electrification study, separate from the existing 2022 dispatch model.

**Sections 1–6 explain provisional budgets for fixed example designs. Section 7 optimizes three real atlas clusters. Section 8 tests uncertainty and break-even thresholds. Section 9 expands to one selected cluster in each of 18 states, using atlas-demand proxies and recovery-service scenarios.** We proceed with available public evidence; measured settlement demand is not required to run these explicitly conditional scenarios. Monetary inputs remain editable analyst assumptions; no observed Sudan price is silently converted to USD, and no damage is inferred from a conflict-risk category.

| Available and checked | Still needed |
|---|---|
| Six-state finite-portfolio planning with national dispatch, four candidate backbone repairs and full-year service checks | Broader design options, surveyed grid/routes, more weather locations, improved demand/access allocation and sequencing |
| Fixed budgets use 100 homes; the pilot uses source cluster sizes and checks identical hourly service across options | Measured diversity/peaks, critical and productive loads, field reliability and multiple weather years |
| Transparent upfront and 20-year costs; point maps across proxy-demand scenarios | A validated construction recommendation or integrated national budget |

The fixed examples in sections 1–6 are **not optimized**. Section 7 separately matches assumed demand across options and checks hourly adequacy. Its conditional rankings depend on provisional routes, equipment prices, service profiles and grid availability; they are not field-validated recommendations.

**Current results: section 12 first.** Supporting reading: 1 Fixed budgets → 2 Cost breakdown → 3 Cash flows and finance → 4 Fixed-design sensitivities → 5 Evidence and assumptions → 6 Accounting checks → 7 Hourly pilot → 8 Uncertainty and break-even → 9 Spatial proxy-demand scenarios across 18 states → 10 Four-cluster joint recovery demonstration → 11 Eight-cluster national dispatch coupling. Section 12 adds the six-state regional scenario study; a country-wide allocation and field-verified rehabilitation plan remain outside its scope.

[Project map](https://github.com/Elgenied/pypsa-sudan) · [Editable inputs and accounting rules](../../data/system_costs/README.md) · [Study plan](https://github.com/Elgenied/pypsa-sudan/blob/main/docs/STUDY_PLAN.md)
''')
code('''from pathlib import Path
import sys, json, subprocess
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from IPython.display import display, Markdown

# Works from this notebook directory or the repository root, including the Desktop copy.
here = Path.cwd().resolve()
ROOT = next(p for p in [here, *here.parents] if (p/'data/system_costs/components.csv').exists())
MODEL = ROOT/'research/system_costs'
sys.path.insert(0, str(MODEL))
from cost_model import evaluate, export_results, read_csv, write_csv, RESULTS, DATA, sensitivity_rows
plt.rcParams.update({'figure.dpi': 125, 'font.size': 11, 'axes.spines.top': False,
                     'axes.spines.right': False, 'axes.titleweight': 'bold'})
pd.set_option('display.max_colwidth', 100)
outputs = export_results()
summary = pd.DataFrame([o['summary'] for o in outputs])
central = summary.query("scenario == 'central'").set_index('case')
labels = {'standalone': 'Standalone\\n100 homes', 'mini_grid': 'Mini-grid\\n100 homes',
          'grid_extension': 'Grid extension\\n5 km new MV', 'grid_repair_extension': 'Grid + repair\\nsynthetic case'}
colors = {'standalone':'#DFAD35','mini_grid':'#269C94','grid_extension':'#446A98','grid_repair_extension':'#8C6AA6'}
def money_table(frame):
    return frame.style.format(precision=0, thousands=',').set_properties(**{'text-align':'right'})
''')
md('''## 1. Results: provisional budgets, not supplier quotations

The accounting horizon is **20 years**, with **10% real discounting** in the central case. Costs are held constant in real terms. “2025 USD” is an **assigned scenario price basis**, not a verified inflation conversion of the older benchmarks. The original evidence keeps its own currency and date.

These four designs all target 1 kWh/home/day, but were selected to demonstrate accounting, not to minimize cost. The grid example assumes a usable upstream source with spare capacity. The repair example adds 2 km of existing MV repair at 50% of a new line's rate and a separate upstream repair allowance. Neither describes surveyed damage.

Annual operating cost excludes replacement purchases, which appear in the cash flows and lifecycle total. All figures below include the assumed nonrecoverable import-tax allowance. An alternative total excluding that allowance is exported separately; it is not a comprehensive social cost-benefit calculation.
''')
code('''view = central[['initial_budget_USD','initial_USD_per_connection','annual_operating_USD','lifecycle_NPC_USD']].copy()
view.columns=['Upfront USD','Upfront USD/home','Annual operations USD','20-year discounted cost USD']
view.index=[labels[x].replace('\\n',' / ') for x in view.index]
display(money_table(view))

fig, axes = plt.subplots(1,2,figsize=(12,4.5), layout='constrained')
for ax, field, title in zip(axes, ['initial_budget_USD','lifecycle_NPC_USD'],
                           ['Upfront project budget','20-year discounted lifecycle cost']):
    vals=central[field]/1000
    bars=ax.bar([labels[x] for x in vals.index], vals, color=[colors[x] for x in vals.index])
    ax.bar_label(bars,fmt='%.0f',padding=4)
    ax.set_ylabel('Thousand planning USD'); ax.set_title(title); ax.set_ylim(0,vals.max()*1.2)
    ax.tick_params(axis='x', labelsize=9)
fig.suptitle('Fixed illustrative designs — adequacy and routes not validated',fontsize=12)
fig.savefig(RESULTS/'budget_overview.png',bbox_inches='tight'); plt.show()
''')
md('''### What is actually being purchased?

The standalone portfolio comprises 100 separate systems, each with 1 kWp PV, 3 kWh **nominal** battery capacity and a 1 kW hybrid inverter. The mini-grid has 50 kWp PV, 150 kWh nominal batteries, a 40 kW battery inverter, a 30 kW diesel generator and 2 km of LV distribution. Battery usable energy, temperature derating and cycling need specification; nominal kWh is not delivered kWh.

Both grid examples include 5 km of new MV, one installed 100 kVA MV/LV transformer, 2 km LV, service drops/meters and basic internal wiring. All four include safe home wiring. Household appliances and productive-use equipment are outside the supply boundary.
''')
code('''boq=pd.read_csv(DATA/'bill_of_quantities.csv')
components=pd.read_csv(DATA/'components.csv')
design_table=boq.merge(components[['component','quantity_unit']],on='component',validate='many_to_one')
display(design_table.pivot(index=['component','quantity_unit'],columns='case',values='quantity').fillna(0).style.format(precision=1))
display(Markdown('Zero in this design table means **not selected**, not a missing price. MV repair is an additional case-design input: 2 route km × 50% of the new-line rate.'))
''')
md('''## 2. What the full mini-grid budget contains

Hardware and installed work are separated. Freight and installation percentages apply only to eligible hardware; an already installed LV line is not charged installation again. The PV inverter and battery inverter have separate roles. A standalone hybrid inverter already includes MPPT, so the model rejects adding another PV inverter to that design.

The source's shipment-cost percentages divide a shipment cost basket; they are **not** percentages to apply to equipment value. Similarly, a published “distribution plus meters per customer” benchmark is only a cross-check, not an extra charge on top of explicit lines and meters.
''')
code('''mg=evaluate('mini_grid')
item_table=pd.DataFrame(mg['items'])[['component','quantity','quantity_unit','unit_cost','cost','life']]
item_table.columns=['Component','Quantity','Unit','Unit price USD','Subtotal USD','Life years']
display(item_table.style.format({'Quantity':'{:,.1f}','Unit price USD':'{:,.0f}','Subtotal USD':'{:,.0f}','Life years':'{:,.0f}'}))
display(money_table(pd.DataFrame.from_dict(mg['initial'],orient='index',columns=['Initial budget USD'])))

groups=pd.DataFrame(mg['items']).groupby('group')['cost'].sum()
groups['Delivery and installation']=sum(mg['initial'][x] for x in ['international_freight','inland_logistics','installation_labour'])
groups['Development and contingency']=mg['initial']['engineering_development']+mg['initial']['contingency']
groups['Assumed import tax']=mg['initial']['assumed_tax']
assert np.isclose(groups.sum(), mg['summary']['initial_budget_USD'])
fig,ax=plt.subplots(figsize=(10,6),layout='constrained')
wedges,_,_=ax.pie(groups,autopct='%1.0f%%',startangle=90,pctdistance=.78,
                  wedgeprops={'width':.43,'edgecolor':'white'},textprops={'fontsize':10})
ax.text(0,0,f"${groups.sum()/1000:,.0f}k\\nupfront",ha='center',va='center',fontsize=17)
ax.legend(wedges,[f'{k}: ${v:,.0f}' for k,v in groups.items()],loc='center left',bbox_to_anchor=(1,.5),frameon=False)
ax.set_title('Mini-grid budget composition | provisional 100-home design')
fig.savefig(RESULTS/'mini_grid_cost_breakdown.png',bbox_inches='tight');plt.show()
display(money_table(pd.DataFrame.from_dict(mg['operating'],orient='index',columns=['Annual operating USD'])))
''')
md(r'''## 3. Replacements, lifecycle cost and financing

The cash-flow ledger records initial investment at year 0 and operations at each year-end. Components are replaced at their assumed life **only before** the end of the study: central-case batteries at years 8 and 16; inverters and the diesel genset at year 10. Replacement prices include applicable delivery, installation, contingency and tax, but initial development is not charged again. Removal/recycling allowances are charged when equipment retires. Prices do not decline automatically.

Baseline residual value is zero. The API can test a straight-line remaining-value credit; that accounting convention is not a resale guarantee. Construction is treated as occurring at commissioning: multi-year construction, interest during construction and working-capital timing require a later dated funding schedule.

$$NPC=C_0+\sum_{t=1}^{T}\frac{O_t+R_t+D_t-S_t}{(1+r)^t},\qquad EAC=NPC\frac{r}{1-(1+r)^{-T}}$$

$O$ is operation, $R$ replacements, $D$ disposal and $S$ residual credit. At zero discount, $EAC=NPC/T$.

The displayed cost per target kWh is $\frac{NPC}{\sum_{t=1}^{T} E_{target,t}/(1+r)^t}$. **It becomes an LCOE only if that delivery is feasible and the operating cost assumptions are consistent with dispatch.** Here demand is constant, hence it also equals EAC/annual target energy. It is not a measured tariff or customer bill.
''')
code('''ledger=pd.DataFrame(mg['ledger'])
annual=ledger.pivot_table(index='year',columns='kind',values='cost_USD',aggfunc='sum',fill_value=0)
fig,ax=plt.subplots(figsize=(12,4.5),layout='constrained')
(annual/1000).plot.bar(stacked=True,ax=ax,width=.85,colormap='Set2')
ax.set_ylabel('Thousand constant planning USD');ax.set_xlabel('Year after commissioning')
ax.set_title('Mini-grid cash spending: replacements are additional to annual O&M')
ax.legend(title='',ncol=3,frameon=False)
fig.savefig(RESULTS/'lifetime_cashflows.png',bbox_inches='tight');plt.show()
display(money_table(annual.loc[[0,1,8,10,16,20]]))

fin=central[['debt_USD','equity_USD','annual_debt_service_USD','year1_operating_plus_debt_USD']].copy()
fin.index=[labels[x].replace('\\n',' / ') for x in fin.index]
display(Markdown('**Financing illustration:** 70% debt, 30% equity, no grant; 10-year loan at 10% real interest. These are scenarios, not available financing terms.'))
display(money_table(fin))
display(Markdown('Debt service is shown for liquidity planning and is **not added to NPC**, which already charges the initial investment and discounts future costs. Year-1 operations plus debt service excludes equity return, replacement reserves and later replacement purchases. Grants reduce sponsor funding, not total system resource requirements.'))
''')
md('''## 4. Which assumptions matter?

The combined lower-input and higher-input cases are stress scenarios, **not confidence intervals**. They change equipment costs, delivery allowances, battery life and financing together. For interpretation, the second chart varies one input at a time from the central case.

Grid distance is route length, not the atlas's straight-line distance to a possibly unsuitable line. No crossing of these curves is reported as an economically validated connection threshold: generation adequacy, grid service and routing have not yet been checked.
''')
code('''comparison=summary.pivot(index='case',columns='scenario',values='conditional_USD_per_target_kWh').reindex(central.index)
comparison=comparison[['lower_input','central','higher_input']]
comparison.index=[labels[x].replace('\\n',' / ') for x in comparison.index]
display(comparison.style.format('{:.2f}').set_caption('Conditional USD per target kWh — no feasibility-certified winner'))

sens=pd.read_csv(RESULTS/'sensitivity.csv')
fig,axes=plt.subplots(1,3,figsize=(14,4.3),layout='constrained')
specs=[('grid_extension','new_MV_route_km','New MV route length (km)'),
       ('mini_grid','battery_life_years','Effective battery life (years)'),
       ('mini_grid','real_discount_rate','Real discount rate (%)')]
for ax,(case,driver,xlabel) in zip(axes,specs):
    s=sens.query('case == @case and driver == @driver').sort_values('value')
    x=s.value*100 if driver=='real_discount_rate' else s.value
    ax.plot(x,s.conditional_USD_per_target_kWh,marker='o',color=colors[case],linewidth=2)
    ax.set_xlabel(xlabel);ax.set_ylabel('Conditional USD / target kWh')
    ax.set_title('Grid extension / route sensitivity' if driver=='new_MV_route_km' else labels[case].replace('\\n',' / '));ax.grid(alpha=.2)
fig.savefig(RESULTS/'sensitivities.png',bbox_inches='tight');plt.show()
''')
md('''## 5. Evidence versus modelling assumptions

**What the Sudan reports actually give us:** dated battery and inverter/panel prices in SDG, indicative local diesel prices, and evidence about delivery/payment constraints. They do not supply a complete compatible system, installation scope, FX rate, verified battery lifespan or current route costs.

The battery table below retains city and date. A 200 Ah battery without voltage cannot be converted into kWh. The panel table's printed “590 kW” is unresolved, so it is not normalized into a panel cost per kW. The separate 550 W interview quote is not used to silently correct that table. Do not combine quotes across dates/specifications into a supposedly contemporaneous turnkey offer.
''')
code('''evidence=ROOT/'data/report_evidence'
if evidence.exists():
    prices=pd.read_csv(evidence/'market_prices_2025.csv')
    batteries=prices.query("product == 'lithium_ion_battery'")
    display(batteries[['data_period','city','price_SDG','nominal_energy_kWh','derived_SDG_per_nominal_kWh']]
            .style.format({'price_SDG':'{:,.0f}','nominal_energy_kWh':'{:,.0f}','derived_SDG_per_nominal_kWh':'{:,.0f}'},na_rep='No quote'))
    fuel=pd.read_csv(evidence/'fuel_prices_2024.csv')
    display(fuel.query("fuel == 'diesel'")[['data_period','location','price_SDG_per_litre','availability']]
            .style.format({'price_SDG_per_litre':'{:,.0f}'},na_rep='No quote'))
else:
    display(Markdown('Local report evidence was not copied here. See the repository data/report_evidence collection.'))
''')
md('''### The editable cost assumptions

All USD values in the next table are **provisional analyst inputs** on the assigned constant-2025 basis. They are neither inferred FX conversions nor automatically inflated historical costs. The anchor column in `components.csv` points to benchmark evidence or explains that a value is an unsourced allowance. Quantity and scope matter as much as unit price.

The ESMAP handbook provides useful historical multi-country component benchmarks; the separate regional grid inputs come from a **South Sudan** study, not Sudan. We use them as context and retain their dates/definitions. The detailed source URLs, page numbers and downloaded-file hashes are in `sources.json` and `benchmark_evidence.csv`.
''')
code('''display(components[['component','quantity_unit','low_USD','base_USD','high_USD','life_years','annual_om_fraction']]
        .style.format({'low_USD':'{:,.0f}','base_USD':'{:,.0f}','high_USD':'{:,.0f}',
                       'life_years':'{:,.0f}','annual_om_fraction':'{:.1%}'}))
params=pd.read_csv(DATA/'scenario_parameters.csv')
display(params[['parameter','lower_input','central','higher_input','unit']].style.format(precision=3))
display(Markdown('Component lifetimes are fixed except battery life, which is overridden by the scenario parameter. Rates use fractions: 0.10 means 10%. A blank source price is never interpreted as zero.'))
''')
md('''## 6. What was checked, what remains missing, and how to use this

The checks below exercise accounting against hand-calculated cases: a zero-interest annuity, loan repayment, a replacement at year 5 but not at retirement, discounted residual value, losses/fuel units, installed-price scope, grant/debt separation and input errors. These validate the implementation's arithmetic, **not the real-world prices or the service feasibility**.
''')
code('''check=subprocess.run([sys.executable,str(MODEL/'check_costs.py')],capture_output=True,text=True)
if check.returncode:
    raise RuntimeError(check.stdout+'\\n'+check.stderr)
validation=json.loads((RESULTS/'validation.json').read_text())
display(pd.DataFrame([validation]))
coverage=pd.read_csv(DATA/'coverage.csv')
display(coverage[['cost_or_requirement','status','needed_to_upgrade']])
''')
md('''### Change one assumption and recalculate

Edit `data/system_costs/components.csv` for prices, equipment life and O&M; `scenario_parameters.csv` for logistics, finance, fuel and effective battery life; `bill_of_quantities.csv` for equipment/route quantities; and `case_designs.csv` for demand, losses and repair assumptions. **Run All** to regenerate every result. Do not edit result CSVs as inputs. Changing quantities does not trigger a capacity optimizer or certify adequacy.

The following example changes mini-grid battery life without changing the source evidence. It does not alter the saved central scenario.
''')
code('''example=evaluate('mini_grid',overrides={'battery_life_years':5})['summary']
display(pd.DataFrame([{'case':'Central: 8-year battery',
                       'NPC_USD':mg['summary']['lifecycle_NPC_USD']},
                      {'case':'Sensitivity: 5-year battery','NPC_USD':example['lifecycle_NPC_USD']}]))
''')
md('''### Use in PyPSA and the next study step

1. Select a small, geographically varied settlement sample. Establish household counts, critical/productive loads and the same hourly service requirement for each option. DRE buildings are not automatically customer accounts.
2. Obtain comparable quotations and route surveys. Replace the highest-impact provisional inputs first: installed MV/LV, usable battery life and price, delivery, repair BOM, bulk supply and delivered fuel. Record quote date, currency, FX convention, specification and what is included.
3. Optimize generation/storage and dispatch chronologically for each candidate service arrangement. Keep battery **energy** and inverter **power** separate. Confirm unmet load, peaks and seasonal performance before computing an LCOE or comparing options.
4. Apply the full cost ledger to feasible designs, then compare under finance, demand, fuel-access and damage scenarios. Shared feeders must be costed once when scaling beyond individual sites.

For a one-year PyPSA objective, `capital_cost` must be periodized, not raw USD/kW CAPEX. Convert USD/kW-year to USD/MW-year (×1,000); storage energy USD/kWh-year to USD/MWh-year (×1,000). A `Store` with charging/discharging `Link`s permits independent power/energy sizing. Link power is defined at its input, so efficiency and rating conventions must be reconciled. Charge the physical bidirectional converter once, not independently on both links. Fixed route/connection costs need activation/choice logic rather than an arbitrary per-MW capacity coefficient.

At the central fuel assumptions, diesel's simple variable electric-output cost is `(1.5 USD/litre × 0.32 litre/kWh + 0.03 USD/kWh) × 1,000 = 510 USD/MWh`. This already uses electrical-output fuel consumption; do not divide by efficiency again. The per-litre input remains provisional and the annual diesel share used in this notebook must be replaced by dispatch.

**Sections 1–6 provide the cost accounting. Section 7 below now applies it to an hourly three-cluster optimization pilot. The 2022 national dispatch model is unchanged and no national least-cost map is claimed.**

### References

- [ESMAP (2022), Mini Grids for Half a Billion People](https://documents1.worldbank.org/curated/en/099635009232259510/pdf/P1751510dd4ab407e083a6098d1905fa94f.pdf), Table 1.4, physical PDF page 85 / printed page 57. Historical benchmarks; not a Sudan quote.
- [World Bank, South Sudan high-level electrification prospectus](https://documents1.worldbank.org/curated/en/099062423121020382/pdf/P175227003a74408f0bc3a075ae51a5747e.pdf), Annex Table 4, PDF pages 27–28. South Sudan planning assumptions, not Sudan observations.
- [Sudan report evidence source register](../../data/report_evidence/source_register.csv): R17, UNDP 2026 solar value-chain study, PDF pages 29 and 31; R12, World Bank August 2024 electricity snapshot, PDF pages 9–10.
- [PyPSA 1.0.6 Generator](https://docs.pypsa.org/v1.0.6/user-guide/components/generators/) and [Store](https://docs.pypsa.org/v1.0.6/user-guide/components/stores/) component documentation.
''')
from pilot_notebook_sections import sections
cells.extend(sections())
from uncertainty_notebook_sections import sections as uncertainty_sections
cells.extend(uncertainty_sections())
from spatial_proxy_notebook_sections import sections as spatial_sections
cells.extend(spatial_sections())
from recovery_notebook_sections import sections as recovery_sections
cells.extend(recovery_sections())
from coupled_notebook_sections import sections as coupled_sections
cells.extend(coupled_sections())
from regional_notebook_sections import sections as regional_sections
cells.extend(regional_sections())
nb=nbf.v4.new_notebook(cells=cells,metadata={'kernelspec':{'display_name':'Python (pypsa)','language':'python','name':'pypsa'},'language_info':{'name':'python'}})
nbf.write(nb,ROOT/'Sudan_System_Costs.ipynb')
print('Built',ROOT/'Sudan_System_Costs.ipynb')
