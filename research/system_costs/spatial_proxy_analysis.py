"""Spatial scenario comparisons with explicit grid-assessment coverage."""
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.colors import ListedColormap
from spatial_proxy_model import DATA,OUT,DESIGN,PRICE

MODES=['standalone','mini_grid','grid_extension']
LABELS={'standalone':'Standalone','mini_grid':'Mini-grid','grid_extension':'Grid + local supply'}
COLORS={'standalone':'#d49a20','mini_grid':'#218d83','grid_extension':'#416e9f'}
DEMAND_LABELS={'atlas_proxy':'Atlas building-demand proxy','recovery_1':'1 kWh / connection / day','recovery_2':'2 kWh / connection / day'}
GRID_LABELS={'continuous':'Continuous upstream supply','evening_interruption':'6-hour evening interruption'}

def write(name,rows):
    df=pd.DataFrame(rows);df.to_csv(OUT/name,index=False,lineterminator='\n');return df

def analyse():
    results=pd.read_csv(OUT/'summary.csv');sites=pd.read_csv(DATA/'sites.csv')
    rows=[];options=[]
    for s in sites.itertuples(index=False):
        for demand in DESIGN['demand_cases']:
            candidates=results[(results.geohash==s.geohash)&(results.demand_case==demand)]
            for grid_case,hours in DESIGN['grid_cases'].items():
                g=candidates[(candidates['mode']!='grid_extension')|(candidates.outage_hours==hours)].sort_values(PRICE)
                assert len(g)==(3 if s.grid_in_local_scope else 2)
                first,second=g.iloc[0],g.iloc[1]
                for r in g.to_dict('records'):options.append(dict(grid_case=grid_case,**r))
                rows.append(dict(sample_id=s.sample_id,state=s.admin_cgaz_1,geohash=s.geohash,source_name=s.village_name,
                    demand_case=demand,grid_case=grid_case,daily_kWh_per_connection=first.daily_kWh_per_connection,
                    annual_delivered_kWh=first.annual_delivered_kWh,service_points=s.num_connections,
                    assessed_options=len(g),grid_in_local_scope=s.grid_in_local_scope,
                    grid_assessment='conditional_local_candidate' if s.grid_in_local_scope else 'not_assessed_outside_local_distance_scope',
                    winner_among_assessed_options=first['mode'],lowest_USD_kWh=first[PRICE],
                    runner_up=second['mode'],runner_up_premium_percent=100*(second[PRICE]/first[PRICE]-1),
                    within_5_percent='; '.join(g.loc[g[PRICE]<=first[PRICE]*(1+DESIGN['near_tie_fraction']),'mode']),
                    initial_budget_USD=first.initial_budget_USD,lifecycle_NPC_USD=first.lifecycle_NPC_USD,
                    equivalent_annual_cost_USD=first.equivalent_annual_cost_USD,pv_kWp=first.pv_kWp,
                    battery_nominal_kWh=first.battery_nominal_kWh,diesel_kW=first.diesel_kW,
                    direct_grid_distance_km=s.distance_to_existing_transmission_lines,
                    chosen_MV_route_proxy_km=first.new_MV_route_proxy_km,chosen_LV_route_proxy_km=first.LV_route_proxy_km))
    winners=write('scenario_choices.csv',rows);options=write('scenario_options.csv',options)
    counts=write('sample_option_counts.csv',winners.groupby(['demand_case','grid_case','grid_assessment','winner_among_assessed_options']).size().reset_index(name='sampled_clusters'))
    totals=[]
    for (demand,grid),g in winners.groupby(['demand_case','grid_case']):
        totals.append(dict(demand_case=demand,grid_case=grid,sampled_clusters=len(g),sample_connections=g.service_points.sum(),
            sample_annual_delivered_MWh=g.annual_delivered_kWh.sum()/1000,sample_initial_budget_USD=g.initial_budget_USD.sum(),
            sample_equivalent_annual_cost_USD=g.equivalent_annual_cost_USD.sum(),
            sample_weighted_USD_kWh=g.equivalent_annual_cost_USD.sum()/g.annual_delivered_kWh.sum(),
            sample_PV_kWp=g.pv_kWp.sum(),sample_battery_kWh=g.battery_nominal_kWh.sum(),
            note='Sum of 18 illustrative independent cases only; no state/national extrapolation or shared-grid optimization'))
    totals=write('sample_totals.csv',totals)
    flips=[]
    for (sid,grid),g in winners.groupby(['geohash','grid_case']):
        g=g.set_index('demand_case');a=g.loc['atlas_proxy'];b=g.loc['recovery_2']
        flips.append(dict(geohash=sid,state=a.state,grid_case=grid,atlas_proxy_choice=a.winner_among_assessed_options,
                         recovery_2_choice=b.winner_among_assessed_options,choice_changes=a.winner_among_assessed_options!=b.winner_among_assessed_options,
                         grid_assessed=bool(a.grid_in_local_scope)))
    changes=write('demand_choice_changes.csv',flips)
    # Sanity checks on the joined comparisons and displayed economic denominators.
    assert len(winners)==len(sites)*len(DESIGN['demand_cases'])*len(DESIGN['grid_cases'])
    assert winners[winners.assessed_options==2].winner_among_assessed_options.ne('grid_extension').all()
    assert np.allclose(winners.lowest_USD_kWh,winners.equivalent_annual_cost_USD/winners.annual_delivered_kWh)
    assert (winners.runner_up_premium_percent>=-1e-8).all()
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    context=pd.read_csv(DATA/'atlas_context_points.csv.gz')
    fig,axes=plt.subplots(2,3,figsize=(13,11),layout='constrained')
    for i,grid in enumerate(DESIGN['grid_cases']):
        for j,demand in enumerate(DESIGN['demand_cases']):
            ax=axes[i,j];ax.scatter(context.lon,context.lat,s=.15,color='#d2d7dc',alpha=.4,rasterized=True)
            view=winners[(winners.grid_case==grid)&(winners.demand_case==demand)].merge(sites[['geohash','lat','lon']],on='geohash',validate='one_to_one')
            for r in view.itertuples(index=False):
                ax.scatter(r.lon,r.lat,s=105,c=COLORS[r.winner_among_assessed_options],edgecolors='#303942',linewidth=.6,
                           marker='o' if r.grid_in_local_scope else '^',zorder=3)
                ax.annotate(str(r.sample_id),(r.lon,r.lat),xytext=(6,6),textcoords='offset points',fontsize=8,zorder=4)
            ax.set_xlim(21,39);ax.set_ylim(9,23);ax.set_aspect(1/np.cos(np.deg2rad(16)))
            ax.set_xlabel('Longitude');ax.set_ylabel('Latitude');ax.grid(alpha=.12)
            ax.set_title(DEMAND_LABELS[demand]+'\n'+GRID_LABELS[grid],fontsize=10)
    handles=[Line2D([0],[0],marker='o',color='none',markerfacecolor=COLORS[m],label=LABELS[m],markersize=8) for m in MODES]
    handles +=[Line2D([0],[0],marker=marker,color='none',markerfacecolor='white',markeredgecolor='#303942',label=label,markersize=8)
               for marker,label in [('o','Grid included conditionally'),('^','Grid not assessed (>50 km source distance)')]]
    fig.legend(handles=handles,loc='outside lower center',ncol=3,fontsize=9,frameon=False)
    fig.suptitle('Lowest-cost option among assessed alternatives at 18 sampled clusters\nDots in grey: atlas locations, not an administrative boundary. Numbers refer to the site table.',fontsize=13)
    fig.savefig(OUT/'spatial_choices.png',dpi=150,bbox_inches='tight');plt.close(fig)

    columns=[(d,g) for d in DESIGN['demand_cases'] for g in DESIGN['grid_cases']]
    codes=np.empty((len(sites),len(columns)));values=np.empty_like(codes)
    for i,s in enumerate(sites.itertuples(index=False)):
        for j,(d,g) in enumerate(columns):
            r=winners[(winners.geohash==s.geohash)&(winners.demand_case==d)&(winners.grid_case==g)].iloc[0]
            codes[i,j]=MODES.index(r.winner_among_assessed_options);values[i,j]=r.lowest_USD_kWh
    fig,ax=plt.subplots(figsize=(12,10),layout='constrained')
    ax.imshow(codes,cmap=ListedColormap([COLORS[m] for m in MODES]),vmin=-.5,vmax=2.5,aspect='auto')
    for i in range(len(sites)):
        for j in range(len(columns)):ax.text(j,i,f'${values[i,j]:.2f}',ha='center',va='center',fontsize=9,color='white' if codes[i,j]>0 else '#20252b')
    ax.set_yticks(range(len(sites)),[f'{r.sample_id}. {r.admin_cgaz_1}'+(' †' if not r.grid_in_local_scope else '') for r in sites.itertuples(index=False)])
    ax.set_xticks(range(len(columns)),[(('Atlas proxy' if d=='atlas_proxy' else d.replace('recovery_','')+' kWh/day')+'\n'+('Firm grid' if g=='continuous' else '6h grid outage')) for d,g in columns],fontsize=9)
    ax.set_title('Sampled cluster choices and lifecycle USD per delivered kWh\n† Grid not assessed; compare standalone and mini-grid only. State labels identify sample locations.',fontsize=12)
    ax.set_xticks(np.arange(-.5,len(columns),1),minor=True);ax.set_yticks(np.arange(-.5,len(sites),1),minor=True)
    ax.grid(which='minor',color='white',linewidth=1.5);ax.tick_params(which='minor',bottom=False,left=False)
    fig.legend(handles=handles[:3],loc='outside lower center',ncol=3,frameon=False)
    fig.savefig(OUT/'state_sample_comparison.png',dpi=150,bbox_inches='tight');plt.close(fig)

    fig,axes=plt.subplots(1,2,figsize=(12,6),layout='constrained')
    x=np.arange(len(sites));width=.26
    for j,d in enumerate(DESIGN['demand_cases']):
        view=winners[(winners.demand_case==d)&(winners.grid_case=='continuous')].sort_values('sample_id')
        axes[0].bar(x+(j-1)*width,view.annual_delivered_kWh/1000,width,label=DEMAND_LABELS[d])
    axes[0].set_xticks(x,sites.sample_id,fontsize=8);axes[0].set_xlabel('Sample ID (see site table)')
    axes[0].set_ylim(0,winners.annual_delivered_kWh.max()/1000*1.3)
    axes[0].set_ylabel('Assumed delivered MWh/year');axes[0].set_title('Available proxy versus chosen recovery service');axes[0].legend(fontsize=8)
    axes[1].barh(sites.admin_cgaz_1,sites.distance_to_existing_transmission_lines,color=np.where(sites.grid_in_local_scope,'#416e9f','#abb3ba'))
    axes[1].axvline(DESIGN['grid_max_straight_distance_km'],color='#a6483d',linestyle='--',label='50 km local-study screen')
    axes[1].set_xscale('log');axes[1].set_xlabel('Atlas distance to line (km; logarithmic scale)')
    axes[1].set_title('Grid evidence and local-study coverage');axes[1].invert_yaxis();axes[1].legend(fontsize=8)
    fig.suptitle('Demand is modelled from buildings; grid proximity does not prove a usable connection',fontsize=12)
    fig.savefig(OUT/'proxy_demand_and_grid_scope.png',dpi=150,bbox_inches='tight');plt.close(fig)
    summary=dict(sampled_clusters=len(sites),states=sites.admin_cgaz_1.nunique(),sample_connections=int(sites.num_connections.sum()),
       grid_conditionally_assessed=int(sites.grid_in_local_scope.sum()),grid_not_assessed=int((~sites.grid_in_local_scope).sum()),
       demand_case_changes={g:int(changes.loc[changes.grid_case==g,'choice_changes'].sum()) for g in DESIGN['grid_cases']},
       counts={f'{d}/{g}':w.winner_among_assessed_options.value_counts().to_dict() for (d,g),w in winners.groupby(['demand_case','grid_case'])},
       interpretation='Counts refer only to selected clusters; no state technology allocation or national investment total.')
    (OUT/'findings.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
    return dict(choices=winners,counts=counts,totals=totals,changes=changes,findings=summary)

if __name__=='__main__':analyse()
