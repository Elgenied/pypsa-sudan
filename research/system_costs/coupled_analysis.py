"""Maps, connection shares and incremental national supply results."""
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch, Wedge
from matplotlib.lines import Line2D
import pypsa
import coupled_model as c

COLORS={'standalone':'#DFA729','mini_grid':'#208D83','grid':'#476DAB'}
LABELS={'standalone':'Standalone','mini_grid':'Mini-grid','grid':'Grid connected'}

def make():
    plt.rcParams.update({'font.size':10,'figure.dpi':140,'axes.spines.top':False,'axes.spines.right':False})
    sites,routes=c.setup();points=sites.set_index('site_id');summary=pd.read_csv(c.OUT/'summary.csv')
    tables=[];directories={};deltas=[]
    baseline=pd.read_csv(c.OUT/'national_base/generation.csv',index_col=0).MWh
    for sc in c.CONFIG['scenario_order']:
        result=json.loads((c.OUT/sc/'summary.json').read_text());folder=c.OUT/sc/result['selected_iteration'];directories[sc]=folder
        tables.append(pd.read_csv(folder/'settlements.csv'))
        generation=pd.read_csv(folder/'national/generation.csv',index_col=0).MWh
        deltas.append((generation-baseline).rename(sc))
    choices=pd.concat(tables,ignore_index=True);choices.to_csv(c.OUT/'settlement_choices.csv',index=False,lineterminator='\n')
    delta=pd.DataFrame(deltas).fillna(0);delta.to_csv(c.OUT/'national_generation_changes_MWh.csv',index_label='scenario',lineterminator='\n')
    national=pypsa.Network(c.DATA/'national_reference.nc')
    fig,axes=plt.subplots(1,2,figsize=(13,7),gridspec_kw={'width_ratios':[1.4,1]})
    ax=axes[0]
    for e in national.links.itertuples():
        a,b=national.buses.loc[e.bus0],national.buses.loc[e.bus1]
        ax.plot([a.x,b.x],[a.y,b.y],color='#B1BAC3',lw=max(.7,e.p_nom/350),zorder=1)
    techcolors={'hydro':'#287EAA','combustible':'#CD8750','other':'#9981B1'}
    capacity=national.generators[national.generators.carrier.isin(techcolors)].groupby(['bus','carrier']).p_nom.sum()
    for bus,b in national.buses.iterrows():
        values=capacity.loc[bus] if bus in capacity.index.get_level_values(0) else pd.Series(dtype=float)
        if values.sum()>0:
            radius=.8*np.sqrt(values.sum()/capacity.groupby(level=0).sum().max());angle=90
            for tech,v in values.items():
                arc=360*v/values.sum();ax.add_patch(Wedge((b.x,b.y),radius,angle,angle+arc,facecolor=techcolors[tech],edgecolor='white',lw=.7,zorder=3));angle+=arc
        if bus in ['Khartoum','Merowe','PortSudan','ElFasher','Nyala','ElGeneina','Kosti','Roseires']:
            ax.annotate(bus,(b.x,b.y),xytext=(5,7 if bus!='Kosti' else -15),textcoords='offset points',fontsize=9)
    root=points.loc['S1'];ax.scatter(root.lon,root.lat,marker='*',s=180,color='#C04460',zorder=5)
    ax.annotate('8-cluster study',(root.lon,root.lat),xytext=(-115,-25),textcoords='offset points',color='#993650',arrowprops={'arrowstyle':'-','color':'#993650'})
    ax.set(xlim=(21.2,39),ylim=(9,22),xlabel='Longitude',ylabel='Latitude',title='National reference supplying the access plan')
    ax.set_aspect(1/np.cos(np.radians(15)));ax.grid(alpha=.15)
    ax.legend(handles=[Patch(color=color,label=tech) for tech,color in techcolors.items()],loc='upper left',fontsize=9,frameon=False)
    largest_capacity=capacity.groupby(level=0).sum().max()
    ax.text(.01,.02,f'Pie area indicates allocated fleet capacity; largest = {largest_capacity:,.0f} MW.\nGrey lines are the 13 schematic reference corridors.',transform=ax.transAxes,fontsize=8)
    ax=axes[1];sc='broad';table=choices.query('scenario == @sc').set_index('site_id');built=pd.read_csv(directories[sc]/'route_build.csv',index_col=0).value
    x=(points.lon-root.lon)*111.32*np.cos(np.radians(root.lat));y=(points.lat-root.lat)*111.32
    for e in routes.itertuples():
        active=built[e.edge_id]>.5;ax.plot(x.loc[[e.from_site,e.to_site]],y.loc[[e.from_site,e.to_site]],color='#476DAB' if active else '#CED3D8',lw=2.5 if active else .9,ls='-' if active else ':',zorder=1)
    offsets={'S1':(-24,2),'S2':(7,8),'S3':(8,-12),'S4':(7,6),'S5':(-23,-14),'S6':(8,-8),'S7':(-25,0),'S8':(8,0)}
    for sid in points.index:
        ax.scatter(x[sid],y[sid],s=40+points.at[sid,'num_connections']*.55,color=COLORS[table.at[sid,'choice']],edgecolor='white',zorder=3)
        ax.annotate(sid,(x[sid],y[sid]),xytext=offsets[sid],textcoords='offset points',fontsize=10)
    ax.set(xlim=(-.8,4),ylim=(-3.3,10.5),xlabel='East of S1 (approx. km)',ylabel='North of S1 (approx. km)',title='Broad local recovery: selected routes')
    ax.grid(alpha=.15);ax.set_aspect('equal')
    ax.legend(handles=[Patch(color=color,label=LABELS[mode]) for mode,color in COLORS.items()],loc='center left',bbox_to_anchor=(1.02,.5),fontsize=8,frameon=False)
    fig.suptitle('Eight clusters linked to the Roseires regional supply balance',fontsize=15)
    fig.text(.5,.025,'Regional-bus assignment is an assumption; no surveyed route from Roseires city is drawn. Local candidates are geometric proxies.',ha='center',fontsize=9)
    fig.tight_layout(rect=(0,.05,1,.94));fig.savefig(c.OUT/'national_coupling_map.png',bbox_inches='tight');plt.close(fig)
    fig,axes=plt.subplots(1,3,figsize=(13,4.8))
    for ax,sc in zip(axes,c.CONFIG['scenario_order']):
        counts=choices.query('scenario == @sc').groupby('choice').connections.sum().reindex(COLORS,fill_value=0);active=counts[counts>0]
        ax.pie(active,labels=[LABELS[k] for k in active.index],colors=[COLORS[k] for k in active.index],startangle=90,autopct=lambda p:f'{p:.0f}%',pctdistance=.8,wedgeprops={'width':.38,'edgecolor':'white'})
        ax.text(0,0,f'{counts.sum():,.0f}\npotential\nconnections',ha='center',va='center');ax.set_title(sc.capitalize()+' local recovery',pad=16)
    fig.suptitle('Same hourly service; national dispatch cost replaces the bulk-price allowance',fontsize=14)
    fig.tight_layout(rect=(0,0,1,.9));fig.savefig(c.OUT/'coupled_connections.png',bbox_inches='tight');plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(12,5));x=np.arange(3);bottom=np.zeros(3)
    local=choices.groupby('scenario').local_EAC_USD.sum().reindex(c.CONFIG['scenario_order'])/1000
    for label,values,color in [('Local systems',local,'#208D83'),('Shared routes / repair',summary.shared_EAC_USD/1000,'#476DAB'),('Additional national generation',summary.incremental_national_dispatch_cost_USD/1000,'#DFA729')]:
        axes[0].bar(x,values,bottom=bottom,label=label,color=color);bottom+=np.asarray(values)
    axes[0].set(ylabel='Thousand USD/year',title='Incremental access lifecycle cost');axes[0].legend(fontsize=9);axes[0].set_ylim(0,bottom.max()*1.4)
    colors={'combustible':'#CD8750','hydro':'#287EAA','imports':'#52A88C','other':'#9981B1'};bottom=np.zeros(3)
    for tech in delta:
        values=delta.loc[c.CONFIG['scenario_order'],tech].to_numpy()
        if np.max(np.abs(values))<.01:continue
        axes[1].bar(x,values,bottom=bottom,label=tech,color=colors.get(tech,'grey'));bottom+=values
    axes[1].set(ylabel='Additional MWh/year',title='Change in national generation');axes[1].legend(fontsize=9)
    for ax in axes:ax.set_xticks(x,['Constrained','Partial','Broad']);ax.grid(axis='y',alpha=.15);ax.set_axisbelow(True)
    fig.text(.5,.02,'Access costs exclude the unchanged baseline national bill. All 8,760 hours are feasible; fixed 2022 fleet and schematic corridors.',ha='center',fontsize=9)
    fig.tight_layout(rect=(0,.06,1,1));fig.savefig(c.OUT/'coupled_costs_supply.png',bbox_inches='tight');plt.close(fig)
    findings=dict(potential_connections=int(sites.num_connections.sum()),allocation={sc:choices.query('scenario == @sc').groupby('choice').connections.sum().astype(int).to_dict() for sc in c.CONFIG['scenario_order']},maximum_coupling_gap_USD=float(summary.certified_absolute_gap_USD.max()),scope='Eight-cluster access allocation coupled to national fixed-fleet dispatch, not national universal access')
    (c.OUT/'findings.json').write_text(json.dumps(findings,indent=2)+'\n');return findings

if __name__=='__main__':print(json.dumps(make()))
