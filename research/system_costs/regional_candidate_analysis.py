"""Saved-output diagnostics and figures for the nested-candidate experiment."""
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
import regional_candidate_diagnostic as study

OUT=study.OUT
COLORS={'grid':'#426BA7','mini_grid':'#1C8D82','standalone':'#E0A324'}
LABELS={'grid':'Grid + local support','mini_grid':'Mini-grid','standalone':'Standalone'}

def make():
    summaries=[];allchoices=[];changes=[];designs=[]
    for sc in ['selective','restored']:
        oldfolder=study.base.OUT/f'{sc}_mixed_36_d1_f1';newfolder=OUT/f'{sc}_expanded'
        old=json.loads((oldfolder/'summary.json').read_text());new=json.loads((newfolder/'summary.json').read_text())
        a=pd.read_csv(oldfolder/'zone_choices.csv');b=pd.read_csv(newfolder/'zone_choices.csv')
        both=a[['zone_id','state','mode','connections','key']].merge(b[['zone_id','mode','key','design_scenario']],on='zone_id',suffixes=('_original','_expanded'),validate='one_to_one')
        both['scenario']=sc;both['mode_changed']=both.mode_original.ne(both.mode_expanded);changes.append(both)
        for label,frame,summary in [('Original',a,old),('Expanded',b,new)]:
            frame=frame.copy();frame['scenario']=sc;frame['library']=label;allchoices.append(frame)
            summaries.append(dict(scenario=sc,library=label,annual_system_cost_USD=summary['annual_system_cost_USD'],local_annual_cost_USD=summary['local_annual_cost_USD'],national_operating_cost_USD=summary['national_operating_cost_USD'],annual_repair_cost_USD=summary['annual_repair_cost_USD'],grid_connections=frame.loc[frame['mode'].eq('grid'),'connections'].sum(),gezira_grid_connections=frame.loc[frame['mode'].eq('grid')&frame.state.eq('Gezira'),'connections'].sum(),grid_import_MWh=frame.grid_import_MWh.sum(),mip_gap=summary['mip_gap']))
        o=pd.read_csv(newfolder/'options.csv');o['scenario']=sc;designs.append(o)
    comparison=pd.DataFrame(summaries);comparison.to_csv(OUT/'comparison.csv',index=False)
    choices=pd.concat(allchoices,ignore_index=True);choices.to_csv(OUT/'all_zone_choices.csv',index=False)
    switches=pd.concat(changes,ignore_index=True);switches.to_csv(OUT/'zone_switches.csv',index=False)
    opts=pd.concat(designs,ignore_index=True);opts[opts.state.eq('Gezira')].to_csv(OUT/'gezira_design_comparison.csv',index=False)
    findings={}
    for sc in ['selective','restored']:
        c=comparison[comparison.scenario.eq(sc)].set_index('library');sw=switches[switches.scenario.eq(sc)]
        findings[sc]=dict(cost_reduction_USD=float(c.at['Original','annual_system_cost_USD']-c.at['Expanded','annual_system_cost_USD']),cost_change_percent=float(100*(c.at['Expanded','annual_system_cost_USD']/c.at['Original','annual_system_cost_USD']-1)),changed_zones=int(sw.mode_changed.sum()),changed_connections_percent=float(100*sw.loc[sw.mode_changed,'connections'].sum()/sw.connections.sum()),gezira_grid_original=int(c.at['Original','gezira_grid_connections']),gezira_grid_expanded=int(c.at['Expanded','gezira_grid_connections']))
        old=json.loads((study.base.OUT/f'{sc}_mixed_36_d1_f1/summary.json').read_text())
        new=json.loads((OUT/f'{sc}_expanded/summary.json').read_text())
        findings[sc]['minimum_cost_reduction_USD']=max(0,old['lower_bound_USD']-new['annual_system_cost_USD'])
        findings[sc]['maximum_cost_reduction_USD']=max(0,old['annual_system_cost_USD']-new['lower_bound_USD'])
    forced=json.loads((OUT/'restored_expanded_gezira_grid/summary.json').read_text());free=json.loads((OUT/'restored_expanded/summary.json').read_text())
    findings['force_all_gezira_grid']=dict(additional_annual_cost_USD=forced['annual_system_cost_USD']-free['annual_system_cost_USD'],minimum_regret_USD=max(0,forced['lower_bound_USD']-free['annual_system_cost_USD']),maximum_regret_USD=max(0,forced['annual_system_cost_USD']-free['lower_bound_USD']),interpretation='System-wide reoptimization; bounded by incumbent and solver lower bounds, not an observed tariff or local willingness to pay.')
    # Candidate-shape diagnostic, all six Gezira zones, identical delivered target.
    g=opts[(opts.scenario=='restored')&opts.state.eq('Gezira')&opts['mode'].eq('grid')]
    design_totals=g.groupby('design_scenario')[['pv_kWp','battery_nominal_kWh','converter_AC_kW','grid_import_MWh','local_EAC_USD']].sum().reindex(study.ORDER)
    library=pd.read_csv(study.lib.OUT/'summary.csv').set_index('key')
    for source in study.ORDER:
        imports=np.zeros(8760)
        for row in g[g.design_scenario.eq(source)].itertuples():
            h=pd.read_csv(study.lib.OUT/library.at[row.key,'hourly_file'],index_col=0,parse_dates=True)
            imports+=h.grid_MW.to_numpy()*row.scale
        design_totals.loc[source,'peak_grid_import_MW']=imports.max()
        evening=np.isin((h.index.hour+2)%24,[18,19,20,21,22,23])
        design_totals.loc[source,'evening_grid_import_MWh']=imports[evening].sum()
    design_totals.to_csv(OUT/'gezira_grid_design_totals.csv')
    plt.rcParams.update({'font.size':10,'figure.dpi':150,'axes.spines.top':False,'axes.spines.right':False})
    cross=pd.read_csv(study.base.DATA/'crosswalk_36.csv.gz')
    # Match the original map's source coordinate column names.
    lon=next(x for x in ['longitude','lon','lng','x'] if x in cross)
    lat=next(x for x in ['latitude','lat','y'] if x in cross)
    fig,axes=plt.subplots(2,2,figsize=(12,13),sharex=True,sharey=True)
    for i,sc in enumerate(['selective','restored']):
        for j,label in enumerate(['Original','Expanded']):
            ax=axes[i,j];rows=choices[(choices.scenario==sc)&(choices.library==label)]
            points=cross.merge(rows[['zone_id','mode']],on='zone_id',validate='many_to_one')
            for mode,color in COLORS.items():
                p=points[points['mode']==mode];ax.scatter(p[lon],p[lat],s=2,c=color,alpha=.7,rasterized=True)
            zones=study.lib.zones(36)
            for state,g in zones.groupby('state'):
                ax.annotate(state,(g.lon.mean(),g.lat.mean()),xytext=(3,5),textcoords='offset points',fontsize=8,bbox={'facecolor':'white','alpha':.7,'edgecolor':'none','pad':1})
            ax.set_aspect(1/np.cos(np.radians(17)))
            ax.set_title(f'{sc.capitalize()} recovery: {label.lower()} candidates');ax.set_xlabel('Longitude' if i else '');ax.set_ylabel('Latitude')
    fig.legend(handles=[Patch(color=c,label=LABELS[k]) for k,c in COLORS.items()],loc='lower center',ncol=3)
    fig.suptitle('Does the regional service choice survive a broader grid-design library?')
    fig.text(.5,.035,'11,268 clusters inherit 36 whole-zone decisions; these are conditional scenarios, not surveyed connection recommendations.',ha='center',fontsize=8)
    fig.tight_layout(rect=[0,.06,1,.96]);fig.savefig(OUT/'candidate_choices_map.png',bbox_inches='tight');fig.savefig(OUT/'candidate_choices_map.svg',bbox_inches='tight');plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(11,4))
    comparison.pivot(index='scenario',columns='library',values='annual_system_cost_USD').reindex(['selective','restored'])[['Original','Expanded']].div(1e9).plot.bar(ax=axes[0],color=['#929ba7','#426BA7'],rot=0)
    axes[0].set_ylabel('Billion constant-2025 USD/year');axes[0].set_title('Full system cost (includes national background)')
    bars=choices[choices.state.eq('Gezira')].groupby(['scenario','library','mode']).connections.sum().unstack(fill_value=0).reindex(columns=COLORS,fill_value=0)
    bars=bars.reindex(pd.MultiIndex.from_product([['selective','restored'],['Original','Expanded']],names=['scenario','library']))
    bars.div(bars.sum(axis=1),axis=0).mul(100).plot.bar(stacked=True,ax=axes[1],color=list(COLORS.values()),rot=25,legend=False)
    axes[1].set_ylabel('% of potential building connections');axes[1].set_title('Gezira: original versus expanded choices');axes[1].set_xlabel('')
    axes[1].set_xticklabels(['Selective\nOriginal','Selective\nExpanded','Restored\nOriginal','Restored\nExpanded'],rotation=0,fontsize=9)
    fig.legend(handles=[Patch(color=c,label=LABELS[k]) for k,c in COLORS.items()],loc='lower center',ncol=3,frameon=False)
    fig.tight_layout(rect=[0,.1,1,1])
    fig.savefig(OUT/'candidate_costs_and_gezira.png',bbox_inches='tight');fig.savefig(OUT/'candidate_costs_and_gezira.svg',bbox_inches='tight');plt.close(fig)
    (OUT/'findings.json').write_text(json.dumps(findings,indent=2))
    print(json.dumps(findings,indent=2));return findings

if __name__=='__main__':make()
