"""Readable figures and decision summaries; scenario counts are never probabilities."""
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from uncertainty_model import OUT, PRICE, DESIGN, MODES

LABELS={'standalone':'Standalone','mini_grid':'Mini-grid','grid_extension':'Grid + local supply'}
COLORS={'standalone':'#d49a20','mini_grid':'#218d83','grid_extension':'#416e9f'}
DRIVERS={'daily_kWh':'Daily demand','pv_cost_factor':'PV equipment cost','battery_cost_factor':'Battery module cost',
         'discount_rate':'Real discount rate','diesel_price':'Delivered diesel price','grid_price':'Bulk grid price',
         'outage_hours':'Evening outage duration','standalone_markup':'Standalone purchase premium',
         'mv_cost_factor':'Installed MV unit cost','lv_length_factor':'LV route length'}

def write(name,rows):
    frame=pd.DataFrame(rows);frame.to_csv(OUT/name,index=False,lineterminator='\n');return frame

def analyse():
    oat=pd.read_csv(OUT/'one_at_a_time.csv');joint=pd.read_csv(OUT/'joint_scenarios.csv')
    sites=oat[['geohash','source_name','pilot_type']].drop_duplicates().reset_index(drop=True)
    base=oat[(oat.axis=='daily_kWh')&(oat.value==1)]
    margins=[];decisions=[];robust=[];outages=[]
    for s in sites.itertuples(index=False):
        bg=base[base.geohash==s.geohash];winner=bg.loc[bg[PRICE].idxmin(),'mode']
        for (axis,value),g in oat[oat.geohash==s.geohash].groupby(['axis','value']):
            costs=g.set_index('mode')[PRICE];best=costs.idxmin();ordered=costs.sort_values()
            gap=100*(costs.drop(winner).min()/costs[winner]-1)
            margins.append(dict(geohash=s.geohash,axis=axis,value=value,base_winner=winner,
                                base_choice_advantage_percent=gap,winner=best))
            decisions.append(dict(geohash=s.geohash,axis=axis,value=value,winner=best,
                     lowest_USD_kWh=ordered.iloc[0],runner_up_premium_percent=100*(ordered.iloc[1]/ordered.iloc[0]-1),
                     within_5_percent='; '.join(costs[costs<=costs.min()*(1+DESIGN['near_tie_fraction'])].index)))
        g=joint[joint.geohash==s.geohash]
        mat=g.pivot(index='joint_scenario',columns='mode',values=PRICE)
        minima=mat.min(axis=1)
        for mode in MODES:
            robust.append(dict(geohash=s.geohash,source_name=s.source_name,mode=mode,scenarios=len(mat),
                 strictly_cheapest_count=int((mat.idxmin(axis=1)==mode).sum()),
                 within_5_percent_count=int((mat[mode]<=minima*(1+DESIGN['near_tie_fraction'])).sum()),
                 min_USD_kWh=mat[mode].min(),max_USD_kWh=mat[mode].max(),
                 max_adaptive_capacity_regret_USD_kWh=(mat[mode]-minima).max(),
                 max_adaptive_capacity_regret_percent=(100*(mat[mode]/minima-1)).max()))
        og=oat[(oat.geohash==s.geohash)&(oat.axis=='outage_hours')]
        x=og.pivot(index='value',columns='mode',values=PRICE).sort_index()
        gap=x.grid_extension-x[['standalone','mini_grid']].min(axis=1)
        crossed=False
        for lo,hi in zip(x.index[:-1],x.index[1:]):
            if gap.loc[lo]*gap.loc[hi]<=0:
                outages.append(dict(geohash=s.geohash,lower_hours_per_day=lo,upper_hours_per_day=hi,
                      status='crossing_between_tested_outage_schedules'));crossed=True
        if not crossed:outages.append(dict(geohash=s.geohash,lower_hours_per_day=x.index.min(),upper_hours_per_day=x.index.max(),
                     status='no_crossing_between_tested_schedules'))
    margins=write('decision_margins.csv',margins);decisions=write('decision_summary.csv',decisions)
    robust=write('scenario_robustness.csv',robust);write('outage_threshold_brackets.csv',outages)
    priorities=[]
    for (sid,axis),g in margins.groupby(['geohash','axis']):
        priorities.append(dict(geohash=sid,driver=axis,
           base_choice_loses_at_any_tested_value=bool((g.base_choice_advantage_percent<0).any()),
           margin_range_percentage_points=g.base_choice_advantage_percent.max()-g.base_choice_advantage_percent.min(),
           minimum_base_choice_advantage_percent=g.base_choice_advantage_percent.min(),
           maximum_base_choice_advantage_percent=g.base_choice_advantage_percent.max()))
    priorities=write('data_priorities.csv',priorities)
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    fig,axes=plt.subplots(2,3,figsize=(14,8),layout='constrained')
    for j,s in enumerate(sites.itertuples(index=False)):
        for i,axis in enumerate(['daily_kWh','outage_hours']):
            ax=axes[i,j];g=oat[(oat.geohash==s.geohash)&(oat.axis==axis)]
            for mode in MODES:
                v=g[g['mode']==mode].sort_values('value')
                ax.plot(v.value,v[PRICE],marker='o',color=COLORS[mode],label=LABELS[mode])
            ax.set_title(s.source_name+'\n'+s.geohash)
            ax.set_xlabel('kWh per service point per day' if i==0 else 'Outage hours/day, beginning 18:00 local')
            ax.set_ylabel('Lifecycle USD / delivered kWh');ax.grid(alpha=.2)
    axes[0,0].legend(fontsize=8)
    fig.suptitle('Re-optimized demand and grid-service sensitivities\nOther assumptions central; connecting lines guide the eye',fontsize=14)
    fig.savefig(OUT/'demand_outage_curves.png',dpi=150,bbox_inches='tight');plt.close(fig)

    fig,axes=plt.subplots(1,3,figsize=(15,7),layout='constrained')
    for ax,s in zip(axes,sites.itertuples(index=False)):
        g=priorities[priorities.geohash==s.geohash].set_index('driver').reindex(DRIVERS)
        y=np.arange(len(g));lo=g.minimum_base_choice_advantage_percent;hi=g.maximum_base_choice_advantage_percent
        ax.hlines(y,lo,hi,color='#416e9f',linewidth=5,alpha=.8)
        ax.scatter(lo,y,color='#416e9f',s=22);ax.scatter(hi,y,color='#416e9f',s=22)
        ax.axvline(0,color='#a6483d',linestyle='--');ax.set_yticks(y,list(DRIVERS.values()),fontsize=9)
        ax.invert_yaxis();ax.grid(axis='x',alpha=.15)
        winner=margins[margins.geohash==s.geohash].base_winner.iloc[0]
        ax.set_title(s.source_name+'\nBase choice: '+LABELS[winner])
        ax.set_xlabel('Base-choice cost advantage (%)\nNegative = another option becomes cheaper')
    fig.suptitle('Which assumptions can overturn the base choice?\nRanges reflect chosen test bounds, not statistical importance or confidence intervals',fontsize=14)
    fig.savefig(OUT/'decision_margin_ranges.png',dpi=150,bbox_inches='tight');plt.close(fig)

    rt=pd.read_csv(OUT/'route_thresholds.csv')
    fig,axes=plt.subplots(1,3,figsize=(14,4.8),layout='constrained')
    for ax,s in zip(axes,sites.itertuples(index=False)):
        g=rt[rt.geohash==s.geohash];energy=base[base.geohash==s.geohash].annual_delivered_kWh.iloc[0]
        roots=g.break_even_new_MV_route_km.dropna()
        xmax=max(5,float(roots.max())*1.5 if len(roots) else 5)
        xx=np.linspace(0,xmax,100)
        for _,r in g.iterrows():
            ax.plot(xx,(r.grid_zero_route_annual_USD+r.MV_annual_USD_per_route_km*xx)/energy,
                    label=f'Grid: {int(r.outage_hours)} h outage/day')
            if np.isfinite(r.break_even_new_MV_route_km):ax.scatter(r.break_even_new_MV_route_km,r.offgrid_annual_USD/energy,s=25)
        ax.axhline(g.offgrid_annual_USD.iloc[0]/energy,color='#202d3a',linestyle='--',label='Cheapest off-grid')
        ax.set_title(s.source_name+f'\nPilot route proxy: {g.assumed_route_km.iloc[0]:.1f} km')
        ax.set_xlabel('Hypothetical new MV route length (km)');ax.set_ylabel('Lifecycle USD / delivered kWh')
        ax.grid(alpha=.2)
    axes[0].legend(fontsize=8)
    fig.suptitle('Grid-distance break-even under fixed losses and a usable 80 kW tie-in',fontsize=13)
    fig.savefig(OUT/'route_break_even.png',dpi=150,bbox_inches='tight');plt.close(fig)

    fig,axes=plt.subplots(1,3,figsize=(14,6),layout='constrained')
    for ax,s in zip(axes,sites.itertuples(index=False)):
        mat=joint[joint.geohash==s.geohash].pivot(index='joint_scenario',columns='mode',values=PRICE).reindex(columns=MODES)
        regret=100*mat.div(mat.min(axis=1),axis=0)-100
        im=ax.imshow(regret,aspect='auto',cmap='YlOrRd',vmin=0,vmax=200)
        ax.set_xticks(range(3),['Standalone','Mini-grid','Grid'],rotation=25,ha='right')
        readable=[n.replace('demand_','D=').replace('_hardware_',' | ').replace('_outage_',' | outage=') for n in mat.index]
        ax.set_yticks(range(len(mat)),readable,fontsize=8)
        for i in range(len(mat)):
            for j in range(3):
                v=regret.iloc[i,j];ax.text(j,i,f'{v:.1f}%',ha='center',va='center',color='white' if v>130 else '#202020',fontsize=9)
        ax.set_title(s.source_name)
    fig.colorbar(im,ax=axes,label='Cost above cheapest option (%) — colour capped at 200%',shrink=.7)
    fig.suptitle('Eight designed joint scenarios: cost of choosing each architecture\nCapacities are re-sized in every cell; this is not fixed-investment regret',fontsize=13)
    fig.savefig(OUT/'joint_scenario_regret.png',dpi=150,bbox_inches='tight');plt.close(fig)
    if (OUT/'demand_thresholds.csv').exists():
        thresholds=pd.read_csv(OUT/'demand_thresholds.csv')
        cases=pd.read_csv(OUT/'optimized_cases.csv')
        samples=[]
        for r in cases.to_dict('records'):
            c=json.loads(r['assumptions_json'])
            if r['mode']!='grid_extension' and set(c)<= {'daily_kWh'}:
                samples.append(dict(geohash=r['geohash'],mode=r['mode'],demand=c.get('daily_kWh',1),cost=r[PRICE]))
        samples=pd.DataFrame(samples)
        fig,axes=plt.subplots(1,3,figsize=(14,4.6),layout='constrained')
        for ax,s in zip(axes,sites.itertuples(index=False)):
            for mode in ['standalone','mini_grid']:
                g=samples[(samples.geohash==s.geohash)&(samples['mode']==mode)].sort_values('demand')
                ax.plot(g.demand,g.cost,'o-',color=COLORS[mode],label=LABELS[mode],markersize=3)
            for r in thresholds[(thresholds.geohash==s.geohash)&(thresholds.status=='sign_change_bracket')].itertuples(index=False):
                ax.axvspan(r.lower_kWh_day,r.upper_kWh_day,color='#416e9f',alpha=.35)
                ax.text(.98,.95,f'Crossing bracket:\n{r.lower_kWh_day:.3f}–{r.upper_kWh_day:.3f} kWh/day',
                        transform=ax.transAxes,ha='right',va='top',fontsize=9)
            ax.set_title(s.source_name);ax.set_xlabel('kWh per service point per day')
            ax.set_ylabel('Lifecycle USD / delivered kWh');ax.grid(alpha=.2)
        axes[0].legend(loc='lower left',fontsize=8)
        fig.suptitle('Mini-grid versus standalone: refined demand crossings\nPairwise comparison; grid may still be cheaper',fontsize=13)
        fig.savefig(OUT/'demand_break_even.png',dpi=150,bbox_inches='tight');plt.close(fig)
    return dict(decisions=decisions,robustness=robust,priorities=priorities)

if __name__=='__main__':analyse()
