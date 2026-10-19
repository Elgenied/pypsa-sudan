"""Plots and comparison tables for the separate section-14 notebook."""
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
import model as m
COLORS={'grid':'#426BA7','mini_grid':'#1C8D82','standalone':'#E0A324'}
LABELS={'grid':'Grid + local support','mini_grid':'Mini-grid','standalone':'Standalone'}

def make():
    m.OUT.mkdir(parents=True,exist_ok=True);rows=[];allchoices=[];flows=[]
    for sc in ['selective','restored']:
        zones,gez,previous,library,repairs,old,off,fixed,physical,unit=m.inputs(sc)
        original=previous[previous.state.eq('Gezira')].reset_index().copy();original['stage']='Section 13';original['scenario']=sc
        original=original.rename(columns={'local_EAC_USD':'local_annual_cost_USD'});allchoices.append(original)
        rows.append(dict(scenario=sc,stage='Section 13',annual_system_cost_USD=old['annual_system_cost_USD'],gezira_local_annual_cost_USD=original.local_annual_cost_USD.sum(),grid_connections=int(original.loc[original['mode'].eq('grid'),'connections'].sum()),potential_connections=int(original.connections.sum()),grid_import_MWh=original.grid_import_MWh.sum(),national_operating_cost_USD=old['national_operating_cost_USD'],pv_MW=original.pv_kWp.sum()/1000,battery_MWh=original.battery_nominal_kWh.sum()/1000,mip_gap=old['mip_gap'],annual_cost_saving_USD=0.))
        for free,label in [(False,'Resize only'),(True,'Resize + choose')]:
            folder=m.OUT/(sc+('_joint_choices' if free else '_fixed_choices'));s=json.loads((folder/'summary.json').read_text());c=pd.read_csv(folder/'choices.csv');c['stage']=label;c['scenario']=sc;allchoices.append(c)
            rows.append(dict(scenario=sc,stage=label,**{k:s[k] for k in ['annual_system_cost_USD','gezira_local_annual_cost_USD','grid_connections','potential_connections','grid_import_MWh','national_operating_cost_USD','mip_gap','annual_cost_saving_USD']},pv_MW=c.pv_kWp.sum()/1000,battery_MWh=c.battery_nominal_kWh.sum()/1000))
            if free:
                local=pd.read_csv(m.OUT/'checked'/(folder.name+'_hourly.csv.gz'),parse_dates=['time_UTC']);aggregates=[]
                for z in c.itertuples():
                    h=local[local.zone_id.eq(z.zone_id)].set_index('time_UTC').copy()
                    h['diesel_MW']=0.
                    if z.mode!='grid':
                        source=pd.read_csv(m.lib.OUT/library.at[z.offgrid_key,'hourly_file'],index_col=0,parse_dates=True);scale=z.target_MWh/365
                        for col in ['pv_MW','diesel_MW','charge_MW','discharge_MW','battery_MWh']:h[col]=source[col]*scale
                    aggregates.append(h[['target_delivered_MW','pv_MW','diesel_MW','grid_MW','charge_MW','discharge_MW','battery_MWh']])
                total=sum(aggregates);total['scenario']=sc;flows.append(total.reset_index())
    table=pd.DataFrame(rows);table['grid_share_percent']=100*table.grid_connections/table.potential_connections;table.to_csv(m.OUT/'comparison.csv',index=False)
    choices=pd.concat(allchoices,ignore_index=True);choices.to_csv(m.OUT/'all_choices.csv',index=False)
    hourly=pd.concat(flows,ignore_index=True);hourly.to_csv(m.OUT/'hourly_gezira.csv.gz',index=False,compression={'method':'gzip','mtime':0})
    plt.rcParams.update({'font.size':10,'figure.dpi':150,'axes.spines.top':False,'axes.spines.right':False})
    stages=['Section 13','Resize only','Resize + choose'];colors=['#939eab','#57a6b0','#426BA7']
    fig,axes=plt.subplots(1,3,figsize=(14,4))
    for ax,col,title,ylabel in zip(axes,['annual_system_cost_USD','grid_share_percent','battery_MWh'],['Annual system cost','Gezira grid service share','Gezira battery capacity'],['Billion constant-2025 USD/year','% of potential connections','MWh (nominal)']):
        t=table.pivot(index='scenario',columns='stage',values=col).reindex(['selective','restored'])[stages]
        if col=='annual_system_cost_USD':t=t/1e9
        t.plot.bar(ax=ax,color=colors,rot=0,legend=False);ax.set_title(title);ax.set_ylabel(ylabel);ax.set_xlabel('')
    fig.legend(handles=[Patch(color=c,label=s) for c,s in zip(colors,stages)],loc='lower center',ncol=3,frameon=False)
    fig.tight_layout(rect=[0,.1,1,1]);save(fig,'joint_comparison')
    cross=pd.read_csv(m.base.DATA/'crosswalk_36.csv.gz');cross=cross[cross.zone_id.str.startswith('Gezira_')]
    fig,axes=plt.subplots(2,3,figsize=(13,9),sharex=True,sharey=True)
    for i,sc in enumerate(['selective','restored']):
        for j,stage in enumerate(stages):
            ax=axes[i,j];c=choices[(choices.scenario==sc)&(choices.stage==stage)]
            points=cross.merge(c[['zone_id','mode']],on='zone_id',validate='many_to_one')
            for mode,color in COLORS.items():
                p=points[points['mode']==mode];ax.scatter(p.lon,p.lat,s=3,c=color,alpha=.7,rasterized=True)
            for z in gez.itertuples():ax.annotate(z.zone_id.replace('Gezira_','Z'),(z.lon,z.lat),fontsize=9,bbox={'facecolor':'white','alpha':.7,'edgecolor':'none'})
            ax.set_title(sc.capitalize()+' — '+stage);ax.set_xlabel('Longitude' if i else '');ax.set_ylabel('Latitude' if j==0 else '');ax.set_aspect(1/np.cos(np.radians(14.5)))
    fig.legend(handles=[Patch(color=c,label=LABELS[k]) for k,c in COLORS.items()],loc='lower center',ncol=3,frameon=False)
    fig.suptitle('Gezira: joint sizing and service choice within six planning zones')
    fig.text(.5,.045,'Points inherit zone decisions. Proxy demand and routes; no settlement-level engineering recommendation.',ha='center',fontsize=9)
    fig.tight_layout(rect=[0,.07,1,.95]);save(fig,'gezira_choices_map')
    fig,axes=plt.subplots(2,1,figsize=(12,7))
    for ax,sc in zip(axes,['selective','restored']):
        h=hourly[hourly.scenario.eq(sc)].set_index('time_UTC');week=h.loc['2022-07-01':'2022-07-07']
        ax.plot(week.index,week.target_delivered_MW,color='black',label='Delivered demand',lw=1.2)
        ax.plot(week.index,week.pv_MW,label='PV generation',color='#e0a324',lw=1)
        ax.plot(week.index,week.grid_MW,label='National grid imports',color='#426BA7',lw=1)
        ax.plot(week.index,week.discharge_MW-week.charge_MW,label='Battery net discharge',color='#1C8D82',lw=1)
        ax.set_title(sc.capitalize()+' — resize + choose, illustrative July week');ax.set_ylabel('MW');ax.grid(alpha=.2)
    axes[0].legend(ncol=4,fontsize=9);fig.text(.5,.01,'Supply includes distribution losses; battery net discharge can be negative when charging. UTC timestamps.',ha='center',fontsize=9)
    fig.tight_layout(rect=[0,.03,1,1]);save(fig,'hourly_operation')
    findings={}
    for sc in ['selective','restored']:
        t=table[table.scenario.eq(sc)].set_index('stage');s=json.loads((m.OUT/f'{sc}_joint_choices/summary.json').read_text())
        c=choices[(choices.scenario==sc)&(choices.stage=='Resize + choose')];o=choices[(choices.scenario==sc)&(choices.stage=='Section 13')]
        change=c[['zone_id','mode','connections']].merge(o[['zone_id','mode']],on='zone_id',suffixes=('_new','_old'));changed=change.mode_new.ne(change.mode_old)
        primary=hourly[hourly.scenario.eq(sc)][['grid_MW','pv_MW','diesel_MW']].sum()
        findings[sc]=dict(joint_pv_MW=float(t.at['Resize + choose','pv_MW']),joint_battery_MWh=float(t.at['Resize + choose','battery_MWh']),national_import_share_of_local_supply_percent=float(100*primary.grid_MW/primary.sum()),resizing_saving_USD=float(t.at['Section 13','annual_system_cost_USD']-t.at['Resize only','annual_system_cost_USD']),additional_service_choice_saving_USD=float(t.at['Resize only','annual_system_cost_USD']-s['annual_system_cost_USD']),gezira_local_cost_reduction_USD=float(t.at['Section 13','gezira_local_annual_cost_USD']-s['gezira_local_annual_cost_USD']),national_operating_cost_increase_USD=float(s['national_operating_cost_USD']-t.at['Section 13','national_operating_cost_USD']),original_cost_USD=float(t.at['Section 13','annual_system_cost_USD']),joint_cost_USD=s['annual_system_cost_USD'],saving_USD=s['annual_cost_saving_USD'],saving_percent=float(100*s['annual_cost_saving_USD']/t.at['Section 13','annual_system_cost_USD']),grid_share_original_percent=float(t.at['Section 13','grid_share_percent']),grid_share_joint_percent=float(t.at['Resize + choose','grid_share_percent']),changed_zones=int(changed.sum()),changed_connections=int(change.loc[changed,'connections'].sum()),mip_gap=s['mip_gap'],minimum_saving_vs_saved_reference_USD=s['annual_cost_saving_USD'],maximum_saving_vs_saved_reference_USD=float(t.at['Section 13','annual_system_cost_USD']-s['resource_cost_lower_bound_USD']))
    fig,axes=plt.subplots(1,2,figsize=(10,4))
    for ax,sc in zip(axes,['selective','restored']):
        energy=hourly[hourly.scenario.eq(sc)][['grid_MW','pv_MW','diesel_MW']].sum()/1000
        keep=energy>1e-6
        labels=np.array(['National grid imports','Local solar','Local diesel'])[keep]
        colors=np.array(['#426BA7','#e0a324','#777777'])[keep]
        ax.pie(energy[keep],labels=labels,colors=colors,autopct='%1.1f%%',startangle=90,wedgeprops={'width':.5},textprops={'fontsize':9})
        ax.set_title(sc.capitalize()+' — annual local supply')
        ax.text(0,0,f'{energy.sum():,.0f}\nGWh',ha='center',va='center')
    fig.text(.5,.01,'Grid imports include national generation of several technologies. Storage is excluded to avoid double counting.',ha='center',fontsize=8)
    fig.tight_layout(rect=[0,.05,1,1]);save(fig,'annual_supply_mix')
    (m.OUT/'findings.json').write_text(json.dumps(findings,indent=2));print(json.dumps(findings,indent=2))

def save(fig,name):
    fig.savefig(m.OUT/(name+'.png'),bbox_inches='tight');fig.savefig(m.OUT/(name+'.svg'),bbox_inches='tight',metadata={'Date':None});plt.close(fig)

if __name__=='__main__':make()
