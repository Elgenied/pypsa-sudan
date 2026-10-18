"""Reader-facing maps and results for the joint recovery demonstration."""
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from matplotlib.ticker import MaxNLocator
import recovery_model as r

COLORS={'standalone':'#DFA729','mini_grid':'#208D83','grid':'#476DAB'}
LABELS={'standalone':'Standalone','mini_grid':'Mini-grid','grid':'Grid connected'}

def make():
    plt.rcParams.update({'font.size':10,'figure.dpi':140,'axes.spines.top':False,'axes.spines.right':False})
    sites,routes,_=r.setup();points=sites.set_index('site_id');summary=pd.read_csv(r.OUT/'summary.csv')
    choices=pd.concat([pd.read_csv(r.OUT/sc/'settlements.csv') for sc in r.CONFIG['scenario_order']],ignore_index=True)
    choices.to_csv(r.OUT/'settlement_choices.csv',index=False,lineterminator='\n')
    fig,axes=plt.subplots(1,3,figsize=(15,6),sharex=True,sharey=True)
    for ax,sc in zip(axes,r.CONFIG['scenario_order']):
        decisions=choices.query('scenario == @sc').set_index('site_id')
        edges=pd.read_csv(r.OUT/sc/'route_build.csv',index_col=0).value
        repair=pd.read_csv(r.OUT/sc/'repair_asset.csv',index_col=0).value
        for edge in routes.itertuples():
            a,b=points.loc[edge.from_site],points.loc[edge.to_site];built=edges[edge.edge_id]>.5
            ax.plot([a.lon,b.lon],[a.lat,b.lat],color='#476DAB' if built else '#CBD1D7',lw=3 if built else .8,ls='-' if built else ':',zorder=1)
        for site in sites.itertuples():
            ax.scatter(site.lon,site.lat,s=site.num_connections*1.8,c=COLORS[decisions.at[site.site_id,'choice']],edgecolors='white',linewidths=1.5,zorder=3)
            offsets={'S1':(-20,-29),'S2':(-8,17),'S3':(-8,-30),'S4':(-8,16)}
            ax.annotate(f'{site.site_id}\n{site.num_connections} connections',(site.lon,site.lat),xytext=offsets[site.site_id],textcoords='offset points',fontsize=9,ha='center',zorder=4)
        ax.set_title(r.CONFIG['scenarios'][sc]['label']+'\n'+('Common feeder repaired' if repair.feeder>.5 else 'Common feeder not repaired'),fontsize=12)
        ax.set_xlabel('Longitude');ax.grid(alpha=.15);ax.set_aspect(1/np.cos(np.radians(sites.lat.mean())))
        ax.xaxis.set_major_locator(MaxNLocator(4))
        ax.set_xlim(sites.lon.min()-.010,sites.lon.max()+.009);ax.set_ylim(sites.lat.min()-.009,sites.lat.max()+.008)
    axes[0].set_ylabel('Latitude')
    handles=[Patch(color=COLORS[k],label=LABELS[k]) for k in COLORS]
    handles += [Line2D([0],[0],color='#476DAB',lw=3,label='Selected new shared route'),Line2D([0],[0],color='#CBD1D7',ls=':',label='Unselected candidate route')]
    fig.legend(handles=handles,loc='lower center',ncol=3,bbox_to_anchor=(.5,.07),frameon=False)
    fig.suptitle('Where does each supply arrangement win? Four neighbouring Blue Nile clusters',fontsize=15,y=.98)
    fig.text(.5,.025,'Point size = potential connections. Routes are geometric candidates, not surveyed lines. The assumed common feeder enters at S1; its path is not mapped.',ha='center',fontsize=9)
    fig.subplots_adjust(top=.83,bottom=.24,wspace=.12)
    fig.savefig(r.OUT/'recovery_choices_map.png',bbox_inches='tight');plt.close(fig)
    # Connections pies show service allocation, not energy sharing or administrative-area winners.
    fig,axes=plt.subplots(1,3,figsize=(13,4.8))
    for ax,sc in zip(axes,r.CONFIG['scenario_order']):
        subset=choices.query('scenario == @sc');counts=subset.groupby('choice').connections.sum().reindex(COLORS,fill_value=0)
        active=counts[counts>0]
        ax.pie(active,labels=[LABELS[k] for k in active.index],colors=[COLORS[k] for k in active.index],autopct=lambda p:f'{p:.0f}%',startangle=90,pctdistance=.78,wedgeprops={'width':.42,'edgecolor':'white'},textprops={'fontsize':10})
        ax.text(0,0,f'{counts.sum():,.0f}\npotential\nconnections',ha='center',va='center',fontsize=11)
        ax.set_title(r.CONFIG['scenarios'][sc]['label'],pad=16)
    fig.suptitle('Service allocation under the same 1 kWh per connection per day target',fontsize=14)
    fig.tight_layout(rect=(0,0,1,.91));fig.savefig(r.OUT/'recovery_connections.png',bbox_inches='tight');plt.close(fig)
    # Separate MW and MWh axes; never mix power and energy in a capacity pie.
    fig,axes=plt.subplots(1,3,figsize=(15,5.7));x=np.arange(3);labels=['Constrained','Partial','Broad']
    local=choices.groupby('scenario').local_equipment_and_operation_EAC_USD.sum().reindex(r.CONFIG['scenario_order']).to_numpy()/1000
    bottom=np.zeros(3)
    parts=[('Local systems',local,'#208D83'),('Shared routes / repairs',summary.shared_asset_EAC_USD.to_numpy()/1000,'#476DAB'),('Regional energy / backup',summary.regional_variable_USD.to_numpy()/1000,'#DFA729'),('Background backup equipment',summary.background_fixed_EAC_USD.to_numpy()/1000,'#8C859F')]
    for label,value,color in parts:axes[0].bar(x,value,bottom=bottom,label=label,color=color);bottom+=value
    axes[0].set_ylabel('Equivalent annual cost (thousand USD/year)');axes[0].set_title('Whole demonstration system cost')
    axes[0].legend(fontsize=8,loc='upper right');axes[0].set_ylim(0,bottom.max()*1.48)
    capacities=choices.groupby('scenario')[['pv_kWp','diesel_kW','battery_nominal_kWh']].sum().reindex(r.CONFIG['scenario_order'])
    axes[1].bar(x-.18,capacities.pv_kWp,width=.36,color='#DFA729',label='PV kWp')
    axes[1].bar(x+.18,capacities.diesel_kW,width=.36,color='#B97761',label='Settlement diesel kW')
    axes[1].set_title('Settlement generation capacities');axes[1].set_ylabel('kW / kWp');axes[1].legend(fontsize=9)
    axes[2].bar(x,capacities.battery_nominal_kWh,color='#8571AB');axes[2].set_title('Settlement battery energy');axes[2].set_ylabel('Nominal kWh')
    for ax in axes:ax.set_xticks(x,labels);ax.grid(axis='y',alpha=.15);ax.set_axisbelow(True)
    fig.suptitle('What changes when more recovery becomes possible?',fontsize=15)
    fig.text(.5,.015,'Constant 2025 USD, 20-year horizon, 10% real discount. Costs include the separate existing-load block; capacity panels cover the four settlements only.',ha='center',fontsize=9)
    fig.tight_layout(rect=(0,.055,1,.94));fig.savefig(r.OUT/'recovery_costs_capacities.png',bbox_inches='tight');plt.close(fig)
    findings=dict(scope='Four neighbouring atlas clusters, not a national allocation',potential_connections=int(sites.num_connections.sum()),
        annual_cost_reduction_constrained_to_broad_USD=float(summary.iloc[0].equivalent_annual_cost_USD-summary.iloc[-1].equivalent_annual_cost_USD),
        allocation={sc:choices.query('scenario == @sc').groupby('choice').connections.sum().astype(int).to_dict() for sc in r.CONFIG['scenario_order']})
    (r.OUT/'findings.json').write_text(json.dumps(findings,indent=2)+'\n');print(json.dumps(findings));return findings

if __name__=='__main__':make()
