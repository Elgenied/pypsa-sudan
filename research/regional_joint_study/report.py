"""Create the regional figures, research tables and executed reader notebook."""
import json
import sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
import nbformat
from nbclient import NotebookClient
from nbconvert import HTMLExporter
import model as m

COLORS={'grid':'#426BA7','mini_grid':'#1C8D82','standalone':'#E0A324'}
LABELS={'grid':'Grid with local support','mini_grid':'Mini-grid','standalone':'Standalone'}
SCENARIOS=['restricted','selective','restored']


def save(fig,name):
    fig.savefig(m.OUT/(name+'.png'),dpi=160,bbox_inches='tight')
    fig.savefig(m.OUT/(name+'.svg'),bbox_inches='tight',metadata={'Date':None})
    plt.close(fig)


def make():
    validation=json.loads((m.OUT/'validation.json').read_text())
    assert validation['passed'] and len(validation['cases'])==12
    summaries=[];choices=[];energy=[];repairs=[]
    for c in m.cases():
        folder=m.OUT/c.key
        assert m.valid(folder,m.fingerprint(c))
        summaries.append(json.loads((folder/'summary.json').read_text()))
        for name,collection in [('choices.csv',choices),('checked/zone_energy.csv',energy),('repairs.csv',repairs)]:
            df=pd.read_csv(folder/name);df['case']=c.key;df['scenario']=c.scenario;df['policy']=c.policy;df['zones']=c.zones;df['demand_factor']=c.demand;df['fuel_factor']=c.fuel
            collection.append(df)
    summary=pd.DataFrame(summaries).drop(columns=['solver_options'])
    chosen=pd.concat(choices,ignore_index=True);annual=pd.concat(energy,ignore_index=True);repair=pd.concat(repairs,ignore_index=True)
    summary['grid_share_percent']=summary.grid_connections/summary.potential_connections*100
    summary.to_csv(m.OUT/'summary.csv',index=False);chosen.to_csv(m.OUT/'all_choices.csv',index=False)
    annual.to_csv(m.OUT/'zone_energy.csv',index=False);repair.to_csv(m.OUT/'all_repairs.csv',index=False)
    state=chosen.groupby(['case','state','mode'],as_index=False).agg(connections=('connections','sum'),target_MWh=('target_MWh','sum'),pv_MW=('pv_kWp',lambda x:x.sum()/1000),battery_MWh=('battery_nominal_kWh',lambda x:x.sum()/1000),diesel_MW=('diesel_kW',lambda x:x.sum()/1000),local_annual_USD=('local_EAC_USD','sum'),initial_USD=('initial_USD','sum'))
    state.to_csv(m.OUT/'state_results.csv',index=False)
    baseline=summary[(summary.zones==36)&(summary.demand==1)&(summary.fuel==1)]
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    fig,axes=plt.subplots(1,3,figsize=(15,7),sharex=True,sharey=True)
    cross=pd.read_csv(m.base.DATA/'crosswalk_36.csv.gz')
    for ax,sc in zip(axes,SCENARIOS):
        c=m.Case(sc);cc=chosen[chosen['case'].eq(c.key)]
        points=cross.merge(cc[['zone_id','mode']],on='zone_id',validate='many_to_one')
        for mode,col in COLORS.items():
            p=points[points['mode'].eq(mode)];ax.scatter(p.lon,p.lat,s=3,c=col,alpha=.65,rasterized=True)
        for state_name,g in points.groupby('admin_cgaz_1'):
            ax.annotate(state_name,(g.lon.mean(),g.lat.mean()),fontsize=8,bbox={'facecolor':'white','alpha':.75,'edgecolor':'none'})
        ax.set_title(sc.capitalize());ax.set_xlabel('Longitude');ax.set_aspect(1/np.cos(np.radians(16)))
    axes[0].set_ylabel('Latitude')
    fig.legend(handles=[Patch(color=v,label=LABELS[k]) for k,v in COLORS.items()],loc='lower center',ncol=3,frameon=False)
    fig.suptitle('Six-state least-cost service choices — 36 planning zones')
    fig.text(.5,.055,'All 11,268 source clusters shown; points inherit their zone decision. Potential connections are not verified households.',ha='center',fontsize=9)
    fig.tight_layout(rect=[0,.09,1,.95]);save(fig,'regional_maps')
    states=m.base.CONFIG['states']
    fig,axes=plt.subplots(6,3,figsize=(10,15))
    for i,st in enumerate(states):
        for j,sc in enumerate(SCENARIOS):
            ax=axes[i,j];d=state[(state['case']==m.Case(sc).key)&(state.state==st)].set_index('mode').connections.reindex(COLORS,fill_value=0)
            active=d>0
            ax.pie(d[active],colors=[COLORS[k] for k in d[active].index],startangle=90,autopct=lambda v:f'{v:.0f}%' if v>=5 else '',wedgeprops={'width':.5},textprops={'fontsize':9})
            if i==0:ax.set_title(sc.capitalize(),fontsize=12)
            if j==0:ax.text(-1.5,0,st,ha='right',va='center',fontsize=10)
    fig.suptitle('Service choice by state — share of potential connections',y=.99)
    fig.legend(handles=[Patch(color=v,label=LABELS[k]) for k,v in COLORS.items()],loc='lower center',ncol=3,frameon=False)
    fig.tight_layout(rect=[.08,.03,1,.97]);save(fig,'state_pies')
    fig,axes=plt.subplots(1,2,figsize=(13,4))
    for ax,col,title in [(axes[0],'annual_system_cost_USD','Annual resource cost (billion USD/year)'),(axes[1],'initial_local_and_repair_USD','Initial local systems + repairs (billion USD)')]:
        table=baseline.pivot(index='scenario',columns='policy',values=col).reindex(SCENARIOS)[['mixed','grid_led','decentralized']]/1e9
        table.columns=['Mixed','Grid-led','Decentralized-first'];table.plot.bar(ax=ax,rot=0,color=['#426BA7','#57a6b0','#E0A324'])
        ax.set_title(title);ax.set_xlabel('');ax.legend(fontsize=8)
    fig.text(.5,.01,'Constant-2025 USD. Annual totals include national background operation; initial spending excludes sunk national generation.',ha='center',fontsize=9)
    fig.tight_layout(rect=[0,.04,1,1]);save(fig,'policy_costs')
    robustness=[]
    ref=chosen[chosen['case']==m.Case('selective').key]
    refpoints=cross.merge(ref[['zone_id','mode']],on='zone_id')[['geohash','mode','num_connections']]
    for c in [m.Case('selective'),*m.cases()[-3:]]:
        cc=chosen[chosen['case']==c.key]
        cw=pd.read_csv(m.base.DATA/f'crosswalk_{c.zones}.csv.gz').merge(cc[['zone_id','mode']],on='zone_id')
        joined=refpoints.merge(cw[['geohash','mode']],on='geohash',suffixes=('_base','_test'),validate='one_to_one')
        changed=joined.mode_base!=joined.mode_test
        row=summary.set_index('case').loc[c.key]
        robustness.append(dict(case=c.key,changed_source_clusters=int(changed.sum()),changed_potential_connections=int(joined.loc[changed,'num_connections'].sum()),changed_connection_share_percent=100*joined.loc[changed,'num_connections'].sum()/joined.num_connections.sum(),annual_system_cost_USD=row.annual_system_cost_USD,grid_share_percent=row.grid_share_percent))
    robust=pd.DataFrame(robustness);robust.to_csv(m.OUT/'robustness.csv',index=False)
    fig,ax=plt.subplots(figsize=(9,4));ax.bar(['Base','48 zones','Demand +20%','Fuel +25%'],robust.grid_share_percent,color='#426BA7');ax.set_ylabel('Grid-labelled potential connections (%)');ax.set_title('Selective recovery: compact robustness checks');fig.tight_layout();save(fig,'robustness')
    fig,axes=plt.subplots(3,1,figsize=(13,9))
    for ax,sc in zip(axes,SCENARIOS):
        h=pd.read_csv(m.OUT/m.Case(sc).key/'checked/state_hourly.csv.gz',parse_dates=['time_UTC']).groupby('time_UTC').sum(numeric_only=True).loc['2022-07-01':'2022-07-07']
        for col,label,color in [('target_delivered_MW','Delivered service','black'),('pv_MW','Local PV','#E0A324'),('grid_MW','Grid imports','#426BA7'),('diesel_MW','Local diesel','#777777')]:ax.plot(h.index,h[col],label=label,color=color,lw=1)
        ax.plot(h.index,h.discharge_MW-h.charge_MW,label='Battery net discharge',color='#1C8D82',lw=1)
        ax.set_title(sc.capitalize());ax.set_ylabel('MW');ax.grid(alpha=.2)
    axes[0].legend(ncol=5,fontsize=8);fig.suptitle('Regional physical operation — illustrative July week, UTC')
    fig.tight_layout(rect=[0,0,1,.97]);save(fig,'hourly_operation')
    findings=[]
    for sc in SCENARIOS:
        d=baseline[baseline.scenario==sc].set_index('policy');a=d.loc['mixed']
        findings.append(dict(scenario=sc,annual_system_cost_USD=float(a.annual_system_cost_USD),initial_USD=float(a.initial_local_and_repair_USD),grid_share_percent=float(a.grid_share_percent),saving_vs_grid_led_USD=float(d.at['grid_led','annual_system_cost_USD']-a.annual_system_cost_USD),saving_vs_decentralized_USD=float(d.at['decentralized','annual_system_cost_USD']-a.annual_system_cost_USD),repair_spend_USD=float(a.repair_investment_USD),gap=float(a.mip_gap),
            **{f'{p}_{suffix}_saving_USD':float(d.at[p,'resource_cost_lower_bound_USD']-a.annual_system_cost_USD if suffix=='minimum' else d.at[p,'annual_system_cost_USD']-a.resource_cost_lower_bound_USD) for p in ['grid_led','decentralized'] for suffix in ['minimum','maximum']}))
    (m.OUT/'findings.json').write_text(json.dumps(findings,indent=2))
    build_notebook()


def build_notebook():
    cells=[]
    def md(t):cells.append(nbformat.v4.new_markdown_cell(t.strip()))
    def code(t):cells.append(nbformat.v4.new_code_cell(t.strip()))
    md('''# Sudan regional recovery: grid rehabilitation, mini-grids and standalone systems

**Research question:** Where, and under what recovery conditions, are grid rehabilitation, mini-grids or standalone systems the least-cost way to provide reliable electricity in northern and central Sudan?

This notebook reports a complete, fixed experiment set for **Northern, River Nile, Khartoum, Gezira, White Nile and Sennar**. It covers all 11,268 source settlement clusters, aggregated into 36 planning zones, and retains national generation and transfers outside the six states. A 48-zone run tests spatial aggregation. The atlas's 10,078,666 potential building connections are not verified households or counts of people lacking electricity.

**Evidence boundary:** the national reference and weather year are 2022; settlement geography and report evidence have their own dates. Recovery scenarios are hypothetical, not observations of current war damage. Hourly local demand is a prescribed service profile. All monetary values are constant-2025 USD under the existing lifecycle ledger. This is a recovery-stage planning study; repair sequencing and year-by-year reconstruction are not optimized.''')
    code('''from pathlib import Path
import json,sys
import pandas as pd
from IPython.display import display,Markdown,Image
here=Path.cwd().resolve()
ROOT=next(p for p in [here,*here.parents] if (p/'data/regional_model/config.json').exists())
STUDY=ROOT/'research/regional_joint_study';R=STUDY/'results'
validation=json.loads((R/'validation.json').read_text());assert validation['passed']
summary=pd.read_csv(R/'summary.csv');choices=pd.read_csv(R/'all_choices.csv')
findings=pd.read_json(R/'findings.json')
display(Markdown(f"**Completed:** {len(summary)} investment cases, each with 8,760 chronological hours and a separate fixed-investment replay. All reported cases passed the saved-output checks."))
for f in findings.itertuples():
    display(Markdown(f"**{f.scenario.capitalize()}:** annual system cost **${f.annual_system_cost_USD/1e9:.3f} billion**; **{f.grid_share_percent:.1f}%** of potential connections assigned grid service; **${f.repair_spend_USD/1e6:.2f} million** of modeled backbone repairs."))''')
    md('''## 1. Study design and fair comparison

| Recovery | Candidate corridor repairs | Local grid interruptions |
|---|---|---|
| Restricted | No repair budget | 18:00–23:00 local time |
| Selective | Endogenous selection within $45 million | 19:00–21:00 local time |
| Restored | All four candidate repairs required | No scheduled local interruption |

For each recovery condition, compare **mixed least-cost planning**, **grid-led** (every zone uses a grid portfolio, with local support allowed), and **decentralized-first** (every zone uses its cheaper mini-grid or standalone design). Every policy faces the same delivered-service target, weather, national system, recovery assumptions and cost basis. The $45 million constraint applies to candidate backbone repairs, not the complete local investment budget.

The mixed model jointly sizes grid-connected PV, battery energy, converter power, hourly imports, national generation/flows and allowed repairs. Independent mini-grid and standalone designs are optimized locally and compared using their complete lifecycle cost. With no trade, shared fuel cap, land cap or budget across off-grid systems, independent sizing is separable. The fuel-price check reoptimizes diesel-capable mini-grids rather than merely repricing their old dispatch.

Demand is allocated consistently: the assumed residential portion of the existing six-state consumption and associated losses is removed before the full selected local service is added. Existing nonresidential demand and demand outside the study area remain. The +20% demand check scales the regional residential service scenario; it does not increase every national load.

Mini-grid systems are replicated across clusters in a planning zone; standalone systems use the existing small-system purchasing premium. A zone is not a single enormous physical mini-grid. Grid portfolios include local network and rehabilitation costs. Network lengths, transformer quantities and tie-ins remain screening proxies; no surveyed feeder routing, voltage or protection study is performed.''')
    code('''coverage=pd.read_csv(ROOT/'data/regional_model/zones_36.csv').groupby('state')[['clusters','connections','baseline_residential_MWh','target_MWh']].sum()
display(coverage.style.format(precision=0,thousands=','))
display(Markdown('The model represents existing service plus the documented service floor. Potential connections must not be reported as newly electrified households.'))''')
    md('''## 2. Where each service option is selected

Each point inherits its planning-zone choice. These are regional screening maps. Grid service may include substantial local PV and storage, and the grid share of connections is different from the share of electricity imported from the national system.''')
    code('''display(Image(filename=str(R/'regional_maps.png')))
display(Image(filename=str(R/'state_pies.png')))''')
    md('''## 3. Costs, policy benchmarks and selected repairs

Annual resource costs include local equipment, replacements, maintenance, connection/rehabilitation costs, security allowances, local diesel operation, actual national generation operation and annualized backbone repairs. Grid energy is not charged again at an illustrative bulk tariff. National background operation is included, so these totals are not simply budgets for new access. The initial-spending metric covers local systems and modeled repairs; historical national generating assets are sunk.

Reported objective bounds refer to the stated technologies, whole-zone decisions and schematic network. They do not certify optimal surveyed routes, probabilistic reliability or unknown demand. A small storage-charging tie-break is removed from reported resource costs.''')
    code('''display(Image(filename=str(R/'policy_costs.png')))
table=summary[['scenario','policy','zones','demand','fuel','annual_system_cost_USD','initial_local_and_repair_USD','grid_share_percent','mip_gap']].copy()
table['annual_system_cost_USD']/=1e9;table['initial_local_and_repair_USD']/=1e9
table=table.rename(columns={'annual_system_cost_USD':'Annual cost (billion USD/year)','initial_local_and_repair_USD':'Initial local + repair (billion USD)','grid_share_percent':'Grid connections (%)'})
display(table.style.format(precision=3))
display(findings[['scenario','saving_vs_grid_led_USD','saving_vs_decentralized_USD']].set_index('scenario').div(1e6).rename(columns={'saving_vs_grid_led_USD':'Saving versus grid-led (million USD/year)','saving_vs_decentralized_USD':'Saving versus decentralized (million USD/year)'}).style.format(precision=2))
display(findings.set_index('scenario').filter(regex='minimum_saving|maximum_saving').div(1e6).style.format(precision=3).set_caption('Solver-bound saving intervals, million USD/year. Intervals spanning zero do not establish a strict ranking.'))
repairs=pd.read_csv(R/'all_repairs.csv');core=[f'{s}_mixed_36_d1_f1' for s in ['restricted','selective','restored']]
display(repairs[repairs['case'].isin(core)][['scenario','asset_id','reference_MW','available_fraction','selected','spend_USD']].style.format(precision=2,thousands=','))''')
    md('''## 4. Physical capacities and electricity supply

Battery power and energy are separate investments; charge and discharge share one AC converter rating. Efficiencies are 95% each way, usable state of charge is 10–90%, and the full year is cyclic. Grid imports cannot reverse to export local PV. Local distribution losses are 10% for grid service, 8% for mini-grids and zero for the standalone accounting boundary. Local diesel remains bounded by the existing energy and power limits.

The national system retains finite generation capacities and annual/monthly hydro energy budgets. Monthly hydro shapes come from the documented historical source, not measured 2022 inflows. There is no new national generation investment or reservoir hydrology model. Repairs restore capacity on four schematic candidate corridors; the recovery labels do not establish actual present-day availability.''')
    code('''state=pd.read_csv(R/'state_results.csv')
display(state[state['case'].isin(core)].groupby(['case','state'])[['pv_MW','battery_MWh','diesel_MW','local_annual_USD','initial_USD']].sum().style.format(precision=1,thousands=','))
energy=pd.read_csv(R/'zone_energy.csv');physical=energy[energy['case'].isin(core)].groupby('scenario')[['target_delivered_MWh','pv_MWh','grid_MWh','diesel_MWh','charge_MWh','discharge_MWh']].sum()/1000
display(physical.rename(columns=lambda x:x.replace('_MWh',' (GWh)')).style.format(precision=1))
display(Image(filename=str(R/'hourly_operation.png')))
display(Markdown('Battery discharge is stored energy, not another primary generation source. PV and imports also supply distribution and storage losses.'))''')
    md('''## 5. Fixed-investment replay and numerical validation

After every investment solve, all capacities, corridor repairs and service choices are fixed. A separate 8,760-hour dispatch optimization rechecks grid and national feasibility. Selected independent off-grid schedules undergo full-year physical checks. No load-shedding generator is allowed in a reported completed case; an infeasible or timed-out case fails the batch and is not silently presented as reliable.

Checks reconstruct electricity balances, weather-derived PV limits, storage chronology, shared converter ratings, outage restrictions, monthly/annual hydro budgets, corridor capacities, coverage, demand allocation, initial costs and the lifecycle objective. Every source cluster is traced to its zone. **Zero unmet modeled load in this synthetic year is not field validation or a probabilistic reliability guarantee.**''')
    code('''checks=[]
for case in validation['cases']:
    for phase in case['phases']:checks.append({'case':case['case'],**phase})
display(pd.DataFrame(checks).style.format(precision=8))''')
    md('''## 6. A small, predetermined robustness set

Selective recovery is rerun with 48 zones, +20% regional residential service, and +25% fuel prices. The fuel change affects national combustible-generation marginal costs and local delivered diesel fuel prices; fixed O&M and equipment prices are unchanged. These are separate one-at-a-time checks, not probability distributions or confidence intervals. The resolution comparison preserves total coverage and bus-level demand but changes both aggregation and the zone weather point. A changed choice therefore cannot be attributed to geometry alone.''')
    code('''display(Image(filename=str(R/'robustness.png')))
display(pd.read_csv(R/'robustness.csv').style.format(precision=2,thousands=','))''')
    md('''## 7. What this study supports, and what remains missing

The study supports conditional regional comparisons of service technologies, modeled repairs, costs and electricity supply under three explicitly defined recovery conditions. It provides a complete reproducible experiment set for the stated six-state planning scope.

Publication claims must retain these limits: assumed household service shapes and sector allocations; one 2022 weather year; historical-shape hydro budgets; schematic corridor ratings and hypothetical damage/repair costs; whole-zone choices; proxy local routes and transformer quantities; and no surveyed settlement engineering. It does not optimize displacement, repair lead times, security events, investment sequencing, detailed feeder voltage or shared inter-cluster mini-grid routing. Those are evidence and model extensions, not properties inferred from a successful solve.

A manuscript should report this as **scenario-based recovery planning using available evidence**, with the geographic and demand limitations stated alongside the maps. Independent evidence review and additional weather/hydro validation would strengthen publication quality. No acceptance or field-implementation readiness is implied.

## 8. Reproduce without an active AI session

From the repository root in the `pypsa` environment:

```powershell
python research/regional_joint_study/run_study.py
```

The driver runs ordinary Python/solver jobs, writes `STATUS.json` and `RUN_STATUS.html`, caches completed cases and resumes after a failure. It performs no language-model or paid AI API calls. The default solver is the available Gurobi installation and requires a valid license; `--solver highs` uses the open-source alternative, potentially with longer runtimes. Four solver threads and one case process at a time bound resource use. Reading this notebook or checking saved outputs requires no Gurobi license.

`model.py` reconstructs custom investment and hydro constraints; NetCDF alone does not contain them. `check.py` independently checks saved results. `report.py` rebuilds the tables, figures and this notebook without new optimization. Solver failures remain in logs; time limits never create a completed result.

Sources and assumptions: [regional model](../../docs/REGIONAL_MODEL.md), [regional scope](../../docs/NORTH_CENTRAL_STUDY.md), [system costs](../../data/system_costs/README.md), and the frozen input manifests. Full experiment outputs are in `results/`; individual case manifests bind inputs and core outputs to checksums.''')
    nb=nbformat.v4.new_notebook(cells=cells,metadata={'kernelspec':{'name':'pypsa','display_name':'Python (pypsa)','language':'python'}})
    # The registered kernel name differs on CI; use the current interpreter via a temporary kernelspec.
    import tempfile
    from jupyter_client import KernelManager
    from jupyter_client.kernelspec import KernelSpecManager
    with tempfile.TemporaryDirectory() as tmp:
        kernel=__import__('pathlib').Path(tmp)/'study';kernel.mkdir()
        (kernel/'kernel.json').write_text(json.dumps({'argv':[sys.executable,'-m','ipykernel_launcher','-f','{connection_file}'],'display_name':'Study Python','language':'python'}))
        manager=KernelSpecManager(kernel_dirs=[tmp])
        km=KernelManager(kernel_name='study',kernel_spec_manager=manager)
        NotebookClient(nb,timeout=600,km=km,resources={'metadata':{'path':str(m.HERE)}}).execute()
    nbformat.write(nb,m.HERE/'Sudan_Regional_Joint_Study.ipynb')
    exporter=HTMLExporter(template_name='lab');exporter.exclude_input=True
    body,_=exporter.from_notebook_node(nb)
    (m.HERE/'Sudan_Regional_Joint_Study.html').write_text(body,encoding='utf-8')


if __name__=='__main__':make()
