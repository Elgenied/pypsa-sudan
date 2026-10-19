"""Build a frozen, executed six-case reading notebook without invoking a solver."""
from pathlib import Path
import datetime
import json
import shutil
import sys
import tempfile
import pandas as pd
import nbformat
from nbclient import NotebookClient
from nbconvert import HTMLExporter
from jupyter_client import KernelManager
from jupyter_client.kernelspec import KernelSpecManager
import model as m


def make():
    cases=[m.Case(s,p) for s in ['restricted','selective'] for p in ['mixed','grid_led','decentralized']]
    output=m.HERE/'interim_6_cases';data=output/'data';data.mkdir(parents=True,exist_ok=True)
    summary=[];choices=[];energy=[];repairs=[];checks=[];hashes={}
    for c in cases:
        folder=m.OUT/c.key
        assert m.valid(folder,m.fingerprint(c)), c.key
        replay_fp=dict(investment_manifest=m.lib.r.sha(folder/'manifest.json'),model=m.lib.r.sha(m.HERE/'model.py'))
        assert m.valid(folder/'replay',replay_fp), c.key
        check_fp=dict(checker=m.lib.r.sha(m.HERE/'check.py'),investment=m.lib.r.sha(folder/'manifest.json'),replay=m.lib.r.sha(folder/'replay/manifest.json'))
        assert m.valid(folder/'checked',check_fp), c.key
        validation=json.loads((folder/'checked/validation.json').read_text())
        assert validation['passed'] and {p['phase'] for p in validation['phases']}=={'investment','replay'}
        assert all(p['passed'] and p['hours']==8760 for p in validation['phases'])
        summary.append(json.loads((folder/'summary.json').read_text()))
        for name,collection in [('choices.csv',choices),('checked/zone_energy.csv',energy),('repairs.csv',repairs)]:
            frame=pd.read_csv(folder/name);frame['case']=c.key;frame['scenario']=c.scenario;frame['policy']=c.policy;collection.append(frame)
        checks.extend(dict(case=c.key,**p) for p in validation['phases'])
        hashes[c.key]={name:m.lib.r.sha(folder/name) for name in ['manifest.json','replay/manifest.json','checked/manifest.json']}
        if c.policy=='mixed':shutil.copy2(folder/'checked/state_hourly.csv.gz',data/(c.scenario+'_hourly.csv.gz'))
    pd.DataFrame(summary).drop(columns='solver_options').to_csv(data/'summary.csv',index=False)
    for name,frames in [('choices',choices),('energy',energy),('repairs',repairs)]:pd.concat(frames,ignore_index=True).to_csv(data/(name+'.csv'),index=False)
    pd.DataFrame(checks).to_csv(data/'validation.csv',index=False)
    shutil.copy2(m.base.DATA/'crosswalk_36.csv.gz',data/'crosswalk_36.csv.gz')
    shutil.copy2(m.base.DATA/'zones_36.csv',data/'zones_36.csv')
    manifest=dict(created_UTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),scope='Frozen interim snapshot: restricted and selective recovery, three policies each; 6 of 12 planned cases.',cases=[c.key for c in cases],source_manifests=hashes,field_validated=False,outputs={p.name:m.lib.r.sha(p) for p in data.iterdir() if p.is_file()})
    (output/'snapshot.json').write_text(json.dumps(manifest,indent=2))
    cells=[]
    def md(text):cells.append(nbformat.v4.new_markdown_cell(text.strip()))
    def code(text):cells.append(nbformat.v4.new_code_cell(text.strip()))
    md('''# Sudan regional recovery — six completed cases

**INTERIM RESULTS: 6 of 12 planned cases.** This notebook contains the three policy comparisons under restricted and selective recovery. Each included case passed investment optimization, an independent 8,760-hour fixed-investment replay, and saved-output physical, cost and coverage checks. Restored recovery and the three robustness checks are **not included**. This is a frozen reading copy; see the parent folder's live progress page for the continuing batch.

**Question:** Where, and under what recovery conditions, are grid rehabilitation, mini-grids or standalone systems the least-cost way to provide reliable electricity in Sudan?

**Region:** Northern, River Nile, Khartoum, Gezira, White Nile and Sennar. All 11,268 source clusters are represented in 36 planning zones. The 10,078,666 potential building connections are **not verified households or newly connected customers**. National generation and electricity transfers outside the six states remain represented.

The reference/weather year is 2022. Recovery conditions are hypothetical; hourly residential demand is an assumed service profile. Numerical validation is not field validation. Monetary values follow the project's constant-2025 USD lifecycle ledger.''')
    code('''from pathlib import Path
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from IPython.display import display,Markdown
HERE=Path.cwd()
if not (HERE/'snapshot.json').exists():
    ROOT=next(p for p in [HERE,*HERE.parents] if (p/'data/regional_model/config.json').exists())
    HERE=ROOT/'research/regional_joint_study/interim_6_cases'
D=HERE/'data';F=HERE/'figures';F.mkdir(exist_ok=True)
snapshot=json.loads((HERE/'snapshot.json').read_text())
summary=pd.read_csv(D/'summary.csv');choices=pd.read_csv(D/'choices.csv')
checks=pd.read_csv(D/'validation.csv');cross=pd.read_csv(D/'crosswalk_36.csv.gz')
scenarios=['restricted','selective'];policies=['mixed','grid_led','decentralized']
policy_labels={'mixed':'Mixed least-cost','grid_led':'Grid-led','decentralized':'Decentralized-first'}
colors={'grid':'#426BA7','mini_grid':'#1C8D82','standalone':'#E0A324'}
labels={'grid':'Grid + local support','mini_grid':'Mini-grid','standalone':'Standalone'}
states=['Northern','River Nile','Khartoum','Gezira','White Nile','Sennar']
plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'figure.dpi':110})
def show(fig,name):
    fig.savefig(F/(name+'.png'),dpi=160,bbox_inches='tight')
    fig.savefig(F/(name+'.svg'),bbox_inches='tight',metadata={'Date':None})
    plt.show();plt.close(fig)
display(Markdown('Snapshot captured **'+snapshot['created_UTC']+'**. Reopening or rerunning this notebook does not run the optimization.'))
assert len(summary)==6 and len(checks)==12 and checks.passed.all()
summary['grid_share_percent']=100*summary.grid_connections/summary.potential_connections
table=summary[['scenario','policy','annual_system_cost_USD','initial_local_and_repair_USD','grid_share_percent','repair_investment_USD']].copy()
table['annual_system_cost_USD']/=1e9;table['initial_local_and_repair_USD']/=1e9;table['repair_investment_USD']/=1e6
table.columns=['Recovery','Policy','Annual cost (billion USD/year)','Initial local + repairs (billion USD)','Grid connections (%)','Backbone repair (million USD)']
display(table.style.format(precision=3))''')
    md('''## 1. What the six cases compare

| Recovery | Backbone repair rule | Assumed local grid interruption |
|---|---|---|
| Restricted | No candidate repairs | 18:00–23:00 local time |
| Selective | Select repairs within $45 million | 19:00–21:00 local time |

Each recovery condition has **mixed least-cost**, **grid-led** and **decentralized-first** policies with identical service targets. The grid-led policy can size local PV and batteries; it does not mean electricity must come entirely from the grid. Decentralized-first chooses the cheaper independent mini-grid or standalone design for each zone. Mixed planning jointly selects grid service, grid-connected equipment and permitted backbone repairs alongside national dispatch. Off-grid designs are independently sized and separable under the stated model.

Existing regional residential consumption is removed from the national baseline before the selected local service is added. Nonresidential demand and outside-region loads remain. Total annual system costs include national background operation, so they are not simply a new-access budget.''')
    code('''coverage=pd.read_csv(D/'zones_36.csv').groupby('state')[['clusters','connections','baseline_residential_MWh','target_MWh']].sum().reindex(states)
display(coverage.style.format(precision=0,thousands=','))''')
    md('''## 2. Maps for all six completed cases

Each point is a source cluster and inherits its planning-zone choice. These are geographic screening maps, not surveyed network routes or individual building recommendations. No administrative boundary or usable connection is inferred from a point's colour.''')
    code('''fig,axes=plt.subplots(2,3,figsize=(16,11),sharex=True,sharey=True)
for i,scenario in enumerate(scenarios):
    for j,policy in enumerate(policies):
        ax=axes[i,j];selected=choices[(choices.scenario==scenario)&(choices.policy==policy)]
        points=cross.merge(selected[['zone_id','mode']],on='zone_id',validate='many_to_one')
        assert len(points)==11268 and points['mode'].notna().all()
        for mode,color in colors.items():
            p=points[points['mode']==mode];ax.scatter(p.lon,p.lat,s=3,c=color,alpha=.7,rasterized=True)
        for state,g in points.groupby('admin_cgaz_1'):
            offset={'White Nile':(-40,0),'Sennar':(15,-10)}.get(state,(0,0))
            ax.annotate(state,(g.lon.mean(),g.lat.mean()),xytext=offset,textcoords='offset points',fontsize=8,bbox={'facecolor':'white','alpha':.8,'edgecolor':'none'})
        ax.set_title(scenario.capitalize()+' / '+policy_labels[policy]);ax.set_aspect(1/np.cos(np.radians(16)))
        if i==1:ax.set_xlabel('Longitude')
        if j==0:ax.set_ylabel('Latitude')
fig.legend(handles=[Patch(color=v,label=labels[k]) for k,v in colors.items()],loc='lower center',ncol=3,frameon=False)
fig.suptitle('Six completed cases — 11,268 clusters, 36 zone decisions')
fig.tight_layout(rect=[0,.045,1,.96]);show(fig,'six_case_maps')''')
    md('''## 3. Regional technology shares in mixed planning

Pies show shares of potential connections, not shares of energy. A grid-labelled zone may use substantial local solar and storage. Slices below 7% are left unlabelled for readability; the table gives the exact connection counts.''')
    code('''fig,axes=plt.subplots(6,2,figsize=(9,15))
mixed=choices[choices.policy=='mixed']
for i,state in enumerate(states):
    for j,scenario in enumerate(scenarios):
        ax=axes[i,j];d=mixed[(mixed.state==state)&(mixed.scenario==scenario)].groupby('mode').connections.sum().reindex(colors,fill_value=0)
        active=d[d>0]
        ax.pie(active,colors=[colors[k] for k in active.index],startangle=90,autopct=lambda v:f'{v:.1f}%' if v>=7 else '',pctdistance=.8,textprops={'fontsize':9},wedgeprops={'width':.5})
        if i==0:ax.set_title(scenario.capitalize())
        if j==0:ax.text(-1.5,0,state,ha='right',va='center')
fig.suptitle('Mixed planning — potential connections by service technology')
fig.legend(handles=[Patch(color=v,label=labels[k]) for k,v in colors.items()],loc='lower center',ncol=3,frameon=False)
fig.tight_layout(rect=[.12,.04,1,.96]);show(fig,'state_pies')
display(mixed.groupby(['scenario','state','mode']).connections.sum().unstack(fill_value=0).style.format(precision=0,thousands=','))''')
    md('''## 4. Policy costs, savings and repairs

Annual costs include lifecycle equipment, replacements, maintenance, local network/security allowances, fuel, national operation and annualized backbone repairs. Initial spending covers local systems and modeled repairs and excludes sunk national generating assets. The storage-charging tie-break is excluded from reported costs.

Savings intervals below use conservative solver objective bounds. An interval spanning zero does not establish a strict cost ranking. These are numerical bounds for this formulation, not uncertainty intervals for real-world costs.''')
    code('''fig,axes=plt.subplots(1,2,figsize=(13,4))
for ax,col,title in [(axes[0],'annual_system_cost_USD','Annual system cost (billion USD/year)'),(axes[1],'initial_local_and_repair_USD','Initial local + repair cost (billion USD)')]:
    t=summary.pivot(index='scenario',columns='policy',values=col).reindex(scenarios)[policies]/1e9
    t.rename(columns=policy_labels).plot.bar(ax=ax,rot=0,color=['#426BA7','#58a6b0','#E0A324'])
    ax.set_title(title);ax.set_xlabel('');ax.legend(fontsize=8)
fig.tight_layout();show(fig,'policy_costs')
savings=[]
for scenario in scenarios:
    s=summary[summary.scenario==scenario].set_index('policy');a=s.loc['mixed']
    for p in ['grid_led','decentralized']:
        b=s.loc[p]
        savings.append({'Recovery':scenario,'Compared with':policy_labels[p],'Saving (million USD/year)':(b.annual_system_cost_USD-a.annual_system_cost_USD)/1e6,'Lower bound':(b.resource_cost_lower_bound_USD-a.annual_system_cost_USD)/1e6,'Upper bound':(b.annual_system_cost_USD-a.resource_cost_lower_bound_USD)/1e6})
display(pd.DataFrame(savings).style.format(precision=3))
repairs=pd.read_csv(D/'repairs.csv')
display(repairs[repairs.policy=='mixed'][['scenario','asset_id','reference_MW','available_fraction','selected','spend_USD']].style.format(precision=2,thousands=','))''')
    md('''## 5. Regional equipment and hourly operation

Mini-grid equipment is replicated across the clusters of a zone; a zone is not one enormous physical mini-grid. Battery energy and AC converter power are sized separately. Storage is cyclic over the full year, with 95% charging/discharging efficiencies and 10–90% state of charge. Distribution losses are 10% for grid service, 8% for mini-grids and zero at the standalone accounting boundary. Battery discharge is stored energy, not another primary energy source.''')
    code('''capacity=mixed.groupby(['scenario','state'])[['pv_kWp','battery_nominal_kWh','converter_AC_kW','diesel_kW']].sum()/1000
capacity.columns=['PV (MW)','Battery (MWh)','Converter (MW)','Diesel (MW)']
display(capacity.style.format(precision=1,thousands=','))
fig,axes=plt.subplots(1,2,figsize=(13,5))
for ax,col in zip(axes,['PV (MW)','Battery (MWh)']):
    capacity[col].unstack('scenario').reindex(states)[scenarios].plot.barh(ax=ax,color=['#777777','#426BA7'])
    ax.set_xlabel(col);ax.set_ylabel('');ax.invert_yaxis()
fig.tight_layout();show(fig,'regional_capacities')
energy=pd.read_csv(D/'energy.csv')
display(energy[energy.policy=='mixed'].groupby('scenario')[['target_delivered_MWh','pv_MWh','grid_MWh','diesel_MWh','charge_MWh','discharge_MWh']].sum().div(1000).rename(columns=lambda s:s.replace('_MWh',' (GWh)')).style.format(precision=1))
fig,axes=plt.subplots(2,1,figsize=(13,7))
for ax,scenario in zip(axes,scenarios):
    h=pd.read_csv(D/(scenario+'_hourly.csv.gz'),parse_dates=['time_UTC']).groupby('time_UTC').sum(numeric_only=True).loc['2022-07-01':'2022-07-07']
    for col,label,color in [('target_delivered_MW','Delivered service','black'),('pv_MW','Local PV','#E0A324'),('grid_MW','Grid imports','#426BA7'),('diesel_MW','Local diesel','#777777')]:ax.plot(h.index,h[col],label=label,color=color,lw=1)
    ax.plot(h.index,h.discharge_MW-h.charge_MW,label='Battery net discharge',color='#1C8D82',lw=1)
    ax.set_title(scenario.capitalize());ax.set_ylabel('MW');ax.grid(alpha=.2)
axes[0].legend(ncol=5,fontsize=8);fig.suptitle('Mixed planning: illustrative July week, UTC')
fig.tight_layout(rect=[0,0,1,.95]);show(fig,'hourly_operation')''')
    md('''## 6. What has been validated

All six investments and six separate fixed-investment dispatch replays passed saved-output checks. Tests cover electrical balances, PV availability, chronological storage, converter limits, local grid interruptions, corridor limits, hydro budgets, source coverage, demand allocation and reconstructed costs. All included cases serve the prescribed hourly load without modeled load shedding.

**This demonstrates numerical feasibility for the assumed year, not independently observed demand, war damage, or probabilistic reliability.** The scenario-based findings remain conditional on schematic corridor capacities, proxy distribution routes/transformers, assumed demand, one weather year, historical hydro seasonality and whole-zone technology choices.''')
    code('''display(checks.style.format(precision=10))
display(summary[['scenario','policy','mip_gap','hours','unserved_MWh']].style.format({'mip_gap':'{:.8%}','hours':'{:.0f}','unserved_MWh':'{:.6f}'}))''')
    md('''## 7. What remains before the full study

- Restored recovery: mixed, grid-led and decentralized-first policies.
- Selective recovery checks: 48 zones, +20% residential service demand and +25% fuel prices.
- Cross-case checks and the complete 12-case notebook.

These six completed cases already support comparisons within restricted and selective recovery. They do not yet establish the results for restored recovery or whether the geographic choices survive the planned robustness checks.

The main batch continues independently. This interim notebook is a frozen snapshot and is not overwritten by the final report. Its data and source-manifest hashes are recorded in `snapshot.json`. Rebuild it from the repository root with `python research/regional_joint_study/interim_report.py`; no solver is invoked. The broader methods and sources remain in [the study guide](../README.md), [regional documentation](../../../docs/REGIONAL_MODEL.md) and [cost evidence](../../../data/system_costs/README.md).''')
    nb=nbformat.v4.new_notebook(cells=cells,metadata={'kernelspec':{'name':'pypsa','display_name':'Python (pypsa)','language':'python'}})
    with tempfile.TemporaryDirectory() as tmp:
        kernel=Path(tmp)/'study';kernel.mkdir()
        (kernel/'kernel.json').write_text(json.dumps({'argv':[sys.executable,'-m','ipykernel_launcher','-f','{connection_file}'],'display_name':'Study Python','language':'python'}))
        km=KernelManager(kernel_name='study',kernel_spec_manager=KernelSpecManager(kernel_dirs=[tmp]))
        NotebookClient(nb,timeout=600,km=km,resources={'metadata':{'path':str(output)}}).execute()
    nbformat.write(nb,output/'Sudan_Regional_Interim.ipynb')
    exporter=HTMLExporter(template_name='lab');exporter.exclude_input=True
    body,_=exporter.from_notebook_node(nb)
    (output/'Sudan_Regional_Interim.html').write_text(body,encoding='utf-8')
    assert all(not any(o.output_type=='error' for o in cell.get('outputs',[])) for cell in nb.cells)
    print('Created executed notebook and HTML:',output,flush=True)


if __name__=='__main__':make()
