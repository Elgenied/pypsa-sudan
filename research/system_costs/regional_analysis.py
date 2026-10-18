"""Coverage, state allocations, recovery projects and benchmark comparisons."""
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
import regional_model as m

COLORS={'grid':'#426BA7','mini_grid':'#1C8D82','standalone':'#E0A324'}
LABELS={'grid':'Grid + local support','mini_grid':'Mini-grid','standalone':'Standalone'}

def weather_resolution(summary):
    """Same twelve cases, same targets: the frozen state-proxy run (commit c509ef0) against per-zone weather points."""
    ref=m.DATA/'state_weather_reference';old=pd.read_csv(ref/'summary.csv').set_index('case');proxies=m.lib.weather();rows=[]
    for r in summary.itertuples():
        o=old.loc[r.case];p=proxies[proxies.zones.eq(r.zones)]
        new=pd.read_csv(m.OUT/r.case/'zone_choices.csv')[['zone_id','mode','connections','clusters']]
        previous=pd.read_csv(ref/f'zone_choices_{r.case}.csv')[['zone_id','mode']].rename(columns={'mode':'mode_state_weather'})
        both=new.merge(previous,on='zone_id',validate='one_to_one');changed=both['mode'].ne(both.mode_state_weather)
        feasible=r.status=='optimal_candidate_portfolio'
        rows.append(dict(case=r.case,status=r.status,
            annual_system_cost_state_weather_USD=o.annual_system_cost_USD,annual_system_cost_zone_weather_USD=r.annual_system_cost_USD,
            cost_change_percent=100*(r.annual_system_cost_USD/o.annual_system_cost_USD-1) if feasible else np.nan,
            unserved_state_weather_MWh=o.unserved_MWh,unserved_zone_weather_MWh=r.unserved_MWh,
            grid_share_state_weather_percent=100*o.grid_connections/o.potential_connections,grid_share_zone_weather_percent=100*r.grid_connections/r.potential_connections,
            mini_grid_share_state_weather_percent=100*o.mini_grid_connections/o.potential_connections,mini_grid_share_zone_weather_percent=100*r.mini_grid_connections/r.potential_connections,
            zones_changing_mode=int(changed.sum()),clusters_changing_mode=int(both.loc[changed,'clusters'].sum()),
            potential_connections_changing_mode=int(both.loc[changed,'connections'].sum()),connection_change_percent=100*both.loc[changed,'connections'].sum()/both.connections.sum(),
            maximum_cluster_distance_state_weather_km=float(p.state_proxy_maximum_cluster_distance_km.max()),maximum_cluster_distance_zone_weather_km=float(p.maximum_cluster_distance_km.max()),
            median_zone_maximum_distance_state_weather_km=float(p.state_proxy_maximum_cluster_distance_km.median()),median_zone_maximum_distance_zone_weather_km=float(p.maximum_cluster_distance_km.median())))
    return pd.DataFrame(rows)

def make():
    plt.rcParams.update({'font.size':10,'figure.dpi':150,'axes.spines.top':False,'axes.spines.right':False,'svg.hashsalt':'pypsa-sudan-regional-v1'})
    summary=pd.read_csv(m.OUT/'summary.csv');zones=pd.read_csv(m.DATA/'zones_36.csv').set_index('zone_id')
    generation=[]
    for r in summary.itertuples():
        g=pd.read_csv(m.OUT/r.case/'generation.csv')
        g=g[~g.carrier.isin(['portfolio_accounting','unserved_diagnostic'])].copy()
        g['case']=r.case;g['scenario']=r.scenario;g['policy']=r.policy;g['status']=r.status;generation.append(g)
    pd.concat(generation,ignore_index=True).to_csv(m.OUT/'national_physical_generation.csv',index=False,lineterminator='\n')
    cross=pd.read_csv(m.DATA/'crosswalk_36.csv.gz')
    base=summary[(summary.zones==36)&(summary.demand_factor==1)&(summary.thermal_cost_factor==1)]
    choices=[]
    for r in base[base.policy.eq('mixed')].itertuples():
        frame=pd.read_csv(m.OUT/r.case/'zone_choices.csv');frame['scenario']=r.scenario;choices.append(frame)
    choices=pd.concat(choices,ignore_index=True)
    totals=choices.groupby(['scenario','state','mode']).agg(potential_connections=('connections','sum'),target_MWh=('target_MWh','sum'),local_EAC_USD=('local_EAC_USD','sum')).reset_index()
    totals.to_csv(m.OUT/'state_allocations.csv',index=False,lineterminator='\n')
    capacities=choices.groupby(['scenario','state']).agg(pv_MW=('pv_kWp','sum'),battery_nominal_MWh=('battery_nominal_kWh','sum'),converter_MW=('converter_AC_kW','sum'),diesel_MW=('diesel_kW','sum'),grid_import_MWh=('grid_import_MWh','sum'),local_diesel_MWh=('diesel_MWh','sum'))
    capacities[['pv_MW','battery_nominal_MWh','converter_MW','diesel_MW']]/=1000
    capacities.to_csv(m.OUT/'state_capacities.csv',lineterminator='\n')
    library=pd.read_csv(m.lib.OUT/'summary.csv').set_index('key')
    annual={key:pd.read_csv(m.lib.OUT/row.hourly_file).select_dtypes('number').sum() for key,row in library.iterrows()}
    energy=[]
    for z in choices.itertuples():
        h=annual[z.key]
        energy.append(dict(scenario=z.scenario,state=z.state,pv_MWh=h.pv_MW*z.scale,diesel_MWh=h.diesel_MW*z.scale,
            grid_import_MWh=h.grid_MW*z.scale,battery_charge_MWh=h.charge_MW*z.scale,battery_discharge_MWh=h.discharge_MW*z.scale,
            delivered_MWh=h.target_delivered_MW*z.scale,local_bus_load_MWh=h.bus_load_MW*z.scale))
    pd.DataFrame(energy).groupby(['scenario','state']).sum().to_csv(m.OUT/'state_energy.csv',lineterminator='\n')
    choices.to_csv(m.OUT/'all_zone_choices.csv',index=False,lineterminator='\n')
    fig,axes=plt.subplots(1,3,figsize=(14,7),sharex=True,sharey=True)
    national=m.coupled.national_network(np.zeros(8760))
    for ax,sc in zip(axes,m.CONFIG['scenarios']):
        table=choices[choices.scenario.eq(sc)].set_index('zone_id')
        cc=cross.merge(table[['mode']],left_on='zone_id',right_index=True,validate='many_to_one')
        ax.scatter(cc.lon,cc.lat,s=1.4,c=cc['mode'].map(COLORS),alpha=.65,rasterized=True)
        for e in national.links.itertuples():
            a,b=national.buses.loc[e.bus0],national.buses.loc[e.bus1]
            ax.plot([a.x,b.x],[a.y,b.y],color='#9DABB7',lw=.65,zorder=0)
        for state,g in zones.groupby('state'):
            ax.annotate(state,(g.lon.mean(),g.lat.mean()),xytext=(3,5),textcoords='offset points',fontsize=8,bbox={'facecolor':'white','alpha':.7,'edgecolor':'none','pad':1})
        ax.set(title=sc.capitalize()+' recovery',xlabel='Longitude',xlim=(cross.lon.min()-.3,cross.lon.max()+.3),ylim=(cross.lat.min()-.3,cross.lat.max()+.3));ax.set_aspect(1/np.cos(np.radians(17)))
    axes[0].set_ylabel('Latitude')
    fig.legend(handles=[Patch(color=v,label=LABELS[k]) for k,v in COLORS.items()],loc='lower center',ncol=3,bbox_to_anchor=(.5,.04),frameon=False)
    fig.suptitle('Six-state coverage: 11,268 source clusters, choices assigned by 36 planning zones with zone weather points',fontsize=13)
    fig.text(.5,.015,'Colours inherit whole-zone decisions; points are not independently optimized connection recommendations. Grey corridors are schematic.',ha='center',fontsize=8)
    fig.tight_layout(rect=(0,.1,1,.93));fig.savefig(m.OUT/'regional_choices_map.png',bbox_inches='tight');fig.savefig(m.OUT/'regional_choices_map.svg',bbox_inches='tight',metadata={'Date':None});plt.close(fig)
    fig,axes=plt.subplots(3,6,figsize=(15,8))
    for i,sc in enumerate(m.CONFIG['scenarios']):
        for j,state in enumerate(m.CONFIG['states']):
            ax=axes[i,j];counts=choices[(choices.scenario.eq(sc))&(choices.state.eq(state))].groupby('mode').connections.sum().reindex(COLORS,fill_value=0)
            active=counts[counts>0]
            ax.pie(active,colors=[COLORS[x] for x in active.index],startangle=90,wedgeprops={'width':.37,'edgecolor':'white'},autopct=lambda p:f'{p:.0f}%' if p>=5 else '',pctdistance=.8,textprops={'fontsize':8})
            ax.text(0,0,f'{counts.sum()/1e6:.2f}m',ha='center',va='center',fontsize=10)
            if i==0:ax.set_title(state)
            if j==0:ax.set_ylabel(sc.capitalize(),labelpad=12)
    fig.suptitle('Potential building connections by selected service arrangement',fontsize=14)
    fig.legend(handles=[Patch(color=v,label=LABELS[k]) for k,v in COLORS.items()],loc='lower center',ncol=3,frameon=False)
    fig.tight_layout(rect=(0,.05,1,.94));fig.savefig(m.OUT/'regional_state_pies.png',bbox_inches='tight');fig.savefig(m.OUT/'regional_state_pies.svg',bbox_inches='tight',metadata={'Date':None});plt.close(fig)
    pivot=base.pivot(index='scenario',columns='policy',values='annual_system_cost_USD').reindex(m.CONFIG['scenarios'])/1e9
    fig,axes=plt.subplots(1,2,figsize=(12,5))
    pivot.rename(columns={'mixed':'Mixed portfolio','grid_led':'Grid-led','decentralized':'Decentralized-first'}).plot.bar(ax=axes[0],rot=0,color=['#DFA729','#476DAB','#208D83'])
    axes[0].set(ylabel='Billion constant-2025 USD/year',xlabel='',title='Same service target, three policies');axes[0].legend(fontsize=8)
    for i,sc in enumerate(pivot.index):
        missing=[p for p in pivot.columns if pd.isna(pivot.at[sc,p])]
        if missing:axes[0].text(i,axes[0].get_ylim()[1]*.04,'Infeasible:\n'+', '.join(x.replace('_',' ') for x in missing),ha='center',fontsize=7,bbox={'facecolor':'white','edgecolor':'none','alpha':.9})
    mix=base[base.policy.eq('mixed')].set_index('scenario').reindex(m.CONFIG['scenarios'])
    mix[['local_annual_cost_USD','national_operating_cost_USD','annual_repair_cost_USD']].rename(columns={'local_annual_cost_USD':'Local systems','national_operating_cost_USD':'National operation','annual_repair_cost_USD':'Backbone repairs'}).div(1e9).plot.bar(stacked=True,ax=axes[1],rot=0,color=['#208D83','#DFA729','#476DAB'])
    axes[1].set(ylabel='Billion constant-2025 USD/year',xlabel='',title='Mixed-portfolio cost components');axes[1].legend(fontsize=8)
    fig.text(.5,.015,'Includes national background operation; not incremental access-only cost. Historical sunk capital is excluded.',ha='center',fontsize=9)
    fig.tight_layout(rect=(0,.05,1,1));fig.savefig(m.OUT/'regional_costs.png',bbox_inches='tight');fig.savefig(m.OUT/'regional_costs.svg',bbox_inches='tight',metadata={'Date':None});plt.close(fig)
    ref=summary[(summary.scenario=='selective')&(summary.policy=='mixed')&(summary.zones==36)&(summary.demand_factor==1)&(summary.thermal_cost_factor==1)].iloc[0]
    checks=summary[(summary.zones==48)|(summary.demand_factor!=1)|(summary.thermal_cost_factor!=1)].copy()
    checks['cost_change_percent']=100*(checks.annual_system_cost_USD/ref.annual_system_cost_USD-1)
    reference_choices=pd.read_csv(m.OUT/ref['case']/'zone_choices.csv')[['zone_id','mode']]
    reference_points=cross.merge(reference_choices,on='zone_id',validate='many_to_one').set_index('geohash')
    for i,row in checks.iterrows():
        repairs=pd.read_csv(m.OUT/row['case']/'repairs.csv')
        checks.loc[i,'selected_repairs']=', '.join(repairs.loc[repairs.selected>.5,'asset_id']) or 'none'
        alternative=pd.read_csv(m.OUT/row['case']/'zone_choices.csv')[['zone_id','mode']]
        points=pd.read_csv(m.DATA/f'crosswalk_{row.zones}.csv.gz').merge(alternative,on='zone_id',validate='many_to_one').set_index('geohash').reindex(reference_points.index)
        changed=points['mode'].ne(reference_points['mode'])
        checks.loc[i,'clusters_changing_mode']=int(changed.sum())
        checks.loc[i,'potential_connections_changing_mode']=int(reference_points.loc[changed,'num_connections'].sum())
        checks.loc[i,'connection_change_percent']=100*reference_points.loc[changed,'num_connections'].sum()/reference_points.num_connections.sum()
    checks.to_csv(m.OUT/'focused_checks.csv',index=False,lineterminator='\n')
    weather_resolution(summary).to_csv(m.OUT/'weather_resolution_check.csv',index=False,lineterminator='\n')
    findings=dict(states=6,clusters=11268,primary_zones=36,regional_cases=len(summary),maximum_mip_gap=float(summary.mip_gap.max()),
        mixed_results=base[base.policy.eq('mixed')][['scenario','annual_system_cost_USD','repair_investment_USD','grid_connections','mini_grid_connections','standalone_connections','unserved_MWh']].to_dict('records'),
        infeasible_benchmarks=summary[summary.status.eq('infeasible_benchmark_diagnostic')][['case','unserved_MWh','shortfall_hours']].to_dict('records'),
        weather_resolution=pd.read_csv(m.OUT/'weather_resolution_check.csv')[['case','cost_change_percent','potential_connections_changing_mode','maximum_cluster_distance_state_weather_km','maximum_cluster_distance_zone_weather_km']].to_dict('records'),
        interpretation='Zone-wide choices from finite candidate portfolios; 2022 reference with dated hydro shapes, one NASA POWER point per zone and hypothetical recovery projects')
    (m.OUT/'findings.json').write_text(json.dumps(findings,indent=2)+'\n');print(json.dumps(findings));return findings

if __name__=='__main__':make()
