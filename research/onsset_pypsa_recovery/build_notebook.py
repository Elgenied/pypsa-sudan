"""Build an executed, readable settlement-screen notebook and HTML."""
from pathlib import Path

import nbformat as nbf
from nbclient import NotebookClient
from nbconvert import HTMLExporter

HERE = Path(__file__).resolve().parent

def m(text):
    return nbf.v4.new_markdown_cell(text)

def c(text):
    return nbf.v4.new_code_cell(text)

cells = [
 m("""# Sudan settlement recovery: OnSSET + PyPSA

**Research question:** Where, and under what recovery conditions, are grid rehabilitation or extension, mini-grids or standalone systems the least-cost way to provide reliable electricity in Sudan?

This is the active entry point. Native OnSSET technology costs screen 11,268 settlements in six states. Three completed PyPSA cases supply recovery assumptions and national/corridor context. The models are linked **one way**; results are conditional rankings, not verified post-war access or project recommendations.

See [method and reproduction](README.md), [guide to previous work](../../docs/WORKSPACE_GUIDE.md) and the [full-year PyPSA study](../regional_joint_study/Sudan_Regional_Joint_Study.ipynb)."""),
 c("""from pathlib import Path
import json, numpy as np, pandas as pd, matplotlib.pyplot as plt
from IPython.display import display
P=Path.cwd(); R=P/'results'
d=pd.read_csv(R/'settlement_screen.csv.gz')
s=pd.read_csv(R/'state_summary.csv')
cases=pd.read_csv(R/'pypsa_case_register.csv')
manifest=json.loads((R/'manifest.json').read_text())
states=['Northern','River Nile','Khartoum','Gezira','White Nile','Sennar']
conditions=['restricted','selective','restored']
colors={'grid':'#4269A5','mini_grid':'#24988B','standalone':'#DEA83C'}
print(f"{manifest['source_clusters']:,} settlements; {len(d):,} scenario rows; OnSSET {manifest['onsset_commit'][:12]}")"""),
 m("""## 1. What the data actually describe

The DRE atlas gives modeled population, building-based *potential* connections, synthetic low-service demand and distance to a mapped existing line. It does not measure access, sales or war damage. This run targets at least 1 kWh/day per potential connection. A line within 50 km is only a grid candidate: voltage, condition, route and spare capacity are unknown. OnSSET's PV/battery packages are simplified cost equivalents without hourly storage or diesel adequacy checks. See the [full assumptions](README.md)."""),
 c("""a=d.loc[d.condition.eq('restored')]
display(pd.DataFrame({'Measure':['Settlements','Modeled population','Potential building connections','Target service, GWh/year','Settlements with raised service floor','Grid candidates within 50 km'],
'Value':[len(a),int(a.population.sum()),int(a.num_connections.sum()),round(a.annual_kWh.sum()/1e6,1),int(a.service_floor_applied.sum()),int((a.grid_distance_km<=50).sum())]}))"""),
 m("""## 2. Recovery scenarios and PyPSA supply context

**Restricted:** no repair, six assumed local outage hours/day. **Selective:** repairs within a $45m budget, three assumed outage hours/day. **Restored:** all four candidate corridors repaired, no scheduled local outage. These are analyst scenarios, not measured outages. The OnSSET grid ranking changes through an explicit $0.45/kWh reliable-backup proxy for outage energy, relative to the $0.15/kWh planning bulk price. Repair spending is shown separately. PyPSA system cost includes national operation and overlaps with the new screen's service costs; **never add the two totals**."""),
 c("""display(cases[['condition','outage_hours_per_day_assumed','selected_repairs','repair_initial_USD','pypsa_annual_system_cost_USD','pypsa_unserved_MWh']].set_index('condition').round(1))"""),
 m("""## 3. Least-cost options across scenarios

Counts below are settlements, not people or confirmed customers. A ranking switch is a response to *assumed* outage cost, not proof that a line can be repaired."""),
 c("""mix=d.groupby(['condition','screen_choice']).size().unstack(fill_value=0).reindex(conditions)[list(colors)]
fig,ax=plt.subplots(figsize=(9,4.3)); left=np.zeros(len(mix))
for mode,color in colors.items():
    ax.barh(mix.index,mix[mode],left=left,color=color,label=mode.replace('_',' ').title());left+=mix[mode].to_numpy()
ax.invert_yaxis();ax.set_xlabel('Atlas settlements');ax.set_title('Conditional least-cost option')
ax.legend(ncol=3,loc='lower center',bbox_to_anchor=(.5,-.38),frameon=False);ax.grid(axis='x',alpha=.2)
plt.tight_layout();plt.show();display(mix)"""),
 m("""## 4. Geographic screening map

Each dot is a settlement centroid. This is not a map of verified electrification, feeder routes or safe field access."""),
 c("""fig,axes=plt.subplots(1,3,figsize=(16,6),sharex=True,sharey=True)
for ax,condition in zip(axes,conditions):
    q=d.loc[d.condition.eq(condition)]
    for mode in ['standalone','mini_grid','grid']:
        z=q.loc[q.screen_choice.eq(mode)];ax.scatter(z.lon,z.lat,s=2.2,c=colors[mode],alpha=.6,rasterized=True)
    ax.set_title(condition.title());ax.set_xlabel('Longitude (°E)');ax.grid(alpha=.15)
axes[0].set_ylabel('Latitude (°N)')
fig.suptitle('Six-state conditional settlement rankings',fontsize=14)
fig.legend(list(colors),ncol=3,loc='lower center',bbox_to_anchor=(.5,-.01),frameon=False)
plt.tight_layout(rect=(0,.05,1,.96));plt.show()"""),
 m("""## 5. State view: restored condition

Pies represent *potential building connections*, not people or metered customers. Grid feasibility still requires feeder and substation surveys."""),
 c("""q=s.loc[s.condition.eq('restored')];fig,axes=plt.subplots(2,3,figsize=(12,7))
for ax,name in zip(axes.flat,states):
    t=q.loc[q.admin_cgaz_1.eq(name)].set_index('screen_choice').reindex(colors).fillna(0)
    values=t.potential_connections.to_numpy()
    ax.pie(values,colors=list(colors.values()),startangle=90,wedgeprops={'width':.42},autopct=lambda x:f'{x:.0f}%' if x>=6 else '',pctdistance=.78)
    ax.text(0,0,f'{values.sum()/1e6:.2f}m',ha='center',va='center');ax.set_title(name)
fig.legend(list(colors),ncol=3,loc='lower center',bbox_to_anchor=(.5,0),frameon=False)
fig.suptitle('Potential connections by option',fontsize=14)
plt.tight_layout(rect=(0,.04,1,.95));plt.show()
display(q.pivot(index='admin_cgaz_1',columns='screen_choice',values='potential_connections').reindex(states).fillna(0).astype(int))"""),
 m("""## 6. How robust are ranking changes?

A small gap between the cheapest and second-cheapest option means the choice may move with better input data. The old atlas security label is not used as a current damage-cost multiplier."""),
 c("""b=d.loc[d.condition.eq('restricted')].set_index('geohash')
e=d.loc[d.condition.eq('restored')].set_index('geohash')
sw=b.screen_choice.ne(e.screen_choice)
v=e[['grid_reliable_lcoe_USD_kWh','mini_grid_lcoe_USD_kWh','standalone_lcoe_USD_kWh']].to_numpy()
margin=np.partition(v,1,axis=1)[:,1]-v.min(axis=1)
display(pd.DataFrame({'Measure':['Changed rankings','Changed with margin under $0.02/kWh','All restored rankings with margin under $0.02/kWh'],
'Count':[int(sw.sum()),int((sw.to_numpy()&(margin<.02)).sum()),int((margin<.02).sum())]}))
display(pd.crosstab(b.screen_choice,e.screen_choice,rownames=['Restricted'],colnames=['Restored']))"""),
 m("""## 7. Validation and the next research step

The code checks settlement coverage, scenario rows, finite selected costs and saved PyPSA case IDs. This establishes computational reproducibility, not empirical validation. For publishable recommendations, verify baseline access, demand and displacement; feeder/substation voltage and spare capacity; surveyed damage and repair costs; and a reliable hourly service target. Calibrate OnSSET cost curves with representative hourly off-grid designs. Then iterate: aggregate candidate grid load to PyPSA buses, optimize supply/repair/dispatch, return bus-specific cost/capacity/reliability to OnSSET, and repeat. See the [workspace guide](../../docs/WORKSPACE_GUIDE.md)."""),
 c("""checks={'Unique settlements per condition':all(d.loc[d.condition.eq(x),'geohash'].is_unique for x in conditions),
'Exactly three rows per settlement':bool(d.geohash.value_counts().eq(3).all()),
'Positive finite selected LCOE':bool(np.isfinite(d.selected_lcoe_USD_kWh).all() and (d.selected_lcoe_USD_kWh>0).all()),
'Case IDs present in PyPSA':set(cases.pypsa_case).issubset(set(pd.read_csv(P/'../regional_joint_study/results/summary.csv').case)),
'Observed access available':manifest['observed_access_status'],'Observed war damage available':manifest['observed_war_damage']}
display(pd.Series(checks,name='Result').to_frame())"""),
]

notebook=nbf.v4.new_notebook(cells=cells,metadata={'kernelspec':{'display_name':'Python (pypsa)','language':'python','name':'python3'}})
NotebookClient(notebook,timeout=180,kernel_name='python3',resources={'metadata':{'path':str(HERE)}}).execute()
path=HERE/'Sudan_OnSSET_PyPSA_Recovery.ipynb'
nbf.write(notebook,path)
html,_=HTMLExporter().from_notebook_node(notebook)
(HERE/'Sudan_OnSSET_PyPSA_Recovery.html').write_text(html,encoding='utf-8')
print(path)
