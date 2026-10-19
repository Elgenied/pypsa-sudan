"""Section 14: Gezira joint grid/PV/storage sizing against national hourly dispatch.
Outside-Gezira portfolios and repairs are fixed at section-13 expanded choices.
"""
from pathlib import Path
from types import SimpleNamespace
import sys,json,argparse,gc
import numpy as np
import pandas as pd
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'system_costs'))
import regional_candidate_diagnostic as ref
from check_coupled import load_network,electrical_checks,TOL
lib=ref.lib;base=ref.base;OUT=HERE/'results'

def inputs(sc):
    zones=lib.zones(36);gez=zones[zones.state.eq('Gezira')].copy()
    folder=ref.OUT/f'{sc}_expanded'
    selected=pd.read_csv(folder/'zone_choices.csv').set_index('zone_id')
    library=pd.read_csv(lib.OUT/'summary.csv').set_index('key')
    repairs=pd.read_csv(folder/'repairs.csv').set_index('asset_id')
    old=json.loads((folder/'summary.json').read_text())
    off=[];fixed={};physical={}
    for z in gez.itertuples():
        options=[lib.package(z,mode,sc,library.reset_index()) for mode in ['standalone','mini_grid']]
        off.append(min(options,key=lambda r:(r['local_EAC_USD'],r['mode'])))
        fixed[z.zone_id]=lib.package(z,'grid',sc,library.reset_index(),equipment=0)['local_EAC_USD']
        h=pd.read_csv(lib.OUT/library.at[lib.key_for(36,z.zone_id,'grid',sc),'hourly_file'],index_col=0,parse_dates=True)
        physical[z.zone_id]=h
    with lib.context(OUT):
        site=SimpleNamespace(num_connections=1000,hull_area=1.,distance_to_existing_transmission_lines=0.)
        _,_,_,_,unit,_=lib.p.cost_context(site,'grid_extension')
    return zones,gez,selected,library,repairs,old,pd.DataFrame(off).set_index('zone_id'),fixed,physical,unit

def fingerprint(sc,free):
    folder=ref.OUT/f'{sc}_expanded'
    return dict(model=lib.r.sha(Path(__file__)),base=base.fingerprints(),reference_manifest=lib.r.sha(folder/'manifest.json'),scenario=sc,free_service_choice=free)

def solve(sc,free=False,solver=None):
    name=sc+('_joint_choices' if free else '_fixed_choices');folder=OUT/name;folder.mkdir(parents=True,exist_ok=True)
    fp=fingerprint(sc,free);marker=folder/'manifest.json'
    if marker.exists():
        m=json.loads(marker.read_text())
        if m['inputs']==fp and all(lib.r.sha(folder/f)==h for f,h in m['outputs'].items()):return json.loads((folder/'summary.json').read_text())
    zones,gez,selected,library,repairs,old,off,fixed,physical,unit=inputs(sc)
    n=base.coupled.national_network(np.zeros(8760));n.remove('Load','additional_access')
    n.add('Carrier',['electricity','local_solar','local_battery','local_import','portfolio_accounting'])
    for bus in zones.supply_bus.unique():
        for suffix in [' consumption',' losses']:n.loads_t.p_set[bus+suffix]*=1-base.CONFIG['residential_share']
    others=selected[selected.state.ne('Gezira')]
    for zid,row in others.iterrows():
        if row['mode']=='grid':
            h=pd.read_csv(lib.OUT/library.at[row.key,'hourly_file'])
            n.add('Load','outside_'+zid,bus=row.supply_bus,p_set=pd.Series(h.grid_MW.to_numpy()*row.scale,index=n.snapshots))
    register=pd.read_csv(base.DATA/'corridor_register.csv').set_index('asset_id')
    for name,r in register.iterrows():
        cap=r.reference_MW
        if r.candidate_repair:cap*=r.available_fraction+(1-r.available_fraction)*repairs.at[name,'selected']
        n.links.at[name,'p_nom']=cap
    eta=lib.r.BASE['battery_discharge_efficiency'];eta_c=lib.r.BASE['battery_charge_efficiency']
    limits={};availability=pd.Series(1.,index=n.snapshots)
    availability.loc[((n.snapshots.hour+2)%24).isin(base.CONFIG['scenarios'][sc]['outage_local_hours'])]=0
    for z in gez.itertuples():
        zid=z.zone_id;scale=z.target_MWh/365;h=physical[zid]
        limits[zid]=dict(pv=5*scale,battery=30*scale,converter=5*scale,grid=scale)
        load=pd.Series(h.target_delivered_MW.to_numpy()*scale/.9,index=n.snapshots)
        n.add('Bus',zid,carrier='electricity',x=z.lon,y=z.lat);n.add('Bus','battery_'+zid,carrier='local_battery')
        n.add('Load','service_'+zid,bus=zid,p_set=load)
        n.add('Generator','cancel_'+zid,bus=zid,carrier='portfolio_accounting',p_nom_extendable=True,p_nom_max=load.max(),p_min_pu=load/load.max(),p_max_pu=load/load.max())
        n.add('Generator','pv_'+zid,bus=zid,carrier='local_solar',p_nom_extendable=True,p_nom_max=limits[zid]['pv'],p_max_pu=pd.Series(h.pv_available_pu.to_numpy(),index=n.snapshots),capital_cost=unit['pv']*1000)
        n.add('Store','store_'+zid,bus='battery_'+zid,carrier='local_battery',e_nom_extendable=True,e_nom_max=limits[zid]['battery'],e_min_pu=.1,e_max_pu=.9,e_cyclic=True,capital_cost=unit['battery']*1000)
        n.add('Link','charge_'+zid,bus0=zid,bus1='battery_'+zid,carrier='local_battery',efficiency=eta_c,p_nom_extendable=True,p_nom_max=limits[zid]['converter'],capital_cost=unit['converter']*1000,marginal_cost=.001)
        n.add('Link','discharge_'+zid,bus0='battery_'+zid,bus1=zid,carrier='local_battery',efficiency=eta,p_nom_extendable=True,p_nom_max=limits[zid]['converter']/eta)
        n.add('Link','import_'+zid,bus0=z.supply_bus,bus1=zid,carrier='local_import',p_nom_extendable=True,p_nom_max=limits[zid]['grid'],p_max_pu=availability)
    budgets=base.monthly_budgets(n);constant=float(others.local_EAC_USD.sum()+old['annual_repair_cost_USD'])
    def extra(network,sns):
        m=network.model;one=m.add_variables(lower=1,upper=1,name='constant_one')
        if free:y=m.add_variables(binary=True,coords=[pd.Index(gez.zone_id,name='zone')],name='grid_choice')
        else:
            y=m.add_variables(lower=0,upper=1,coords=[pd.Index(gez.zone_id,name='zone')],name='grid_choice')
            for zid in gez.zone_id:m.add_constraints(y.sel(zone=zid)==int(selected.at[zid,'mode']=='grid'),name='fixed_choice_'+zid)
        cap=m.variables['Link-p_nom'];flow=m.variables['Link-p']
        for z in gez.itertuples():
            zid=z.zone_id;g=y.sel(zone=zid);lim=limits[zid]
            m.add_constraints(m.variables['Generator-p_nom'].sel(name='cancel_'+zid)==n.loads_t.p_set['service_'+zid].max()*(one-g),name='cancel_service_'+zid)
            m.add_constraints(m.variables['Generator-p_nom'].sel(name='pv_'+zid)<=lim['pv']*g,name='gate_pv_'+zid)
            m.add_constraints(m.variables['Store-e_nom'].sel(name='store_'+zid)<=lim['battery']*g,name='gate_battery_'+zid)
            m.add_constraints(cap.sel(name='charge_'+zid)<=lim['converter']*g,name='gate_converter_'+zid)
            m.add_constraints(cap.sel(name='import_'+zid)<=lim['grid']*g,name='gate_grid_'+zid)
            m.add_constraints(cap.sel(name='charge_'+zid)==eta*cap.sel(name='discharge_'+zid),name='shared_converter_'+zid)
            m.add_constraints(flow.sel(name='charge_'+zid)+eta*flow.sel(name='discharge_'+zid)<=cap.sel(name='charge_'+zid),name='converter_throughput_'+zid)
        for b in budgets.itertuples():m.add_constraints(m.variables['Generator-p'].sel(name=b.generator,snapshot=sns[sns.month==b.month]).sum()<=b.budget_MWh,name=b.generator.replace(' ','_')+f'_m{b.month}')
        m.objective+=constant*one+sum(fixed[zid]*y.sel(zone=zid)+off.at[zid,'local_EAC_USD']*(one-y.sel(zone=zid)) for zid in gez.zone_id)
    print('SOLVE',folder.name,flush=True)
    (folder/'solver.log').write_text('')
    # The restored mixed-integer case is numerically slow in HiGHS 1.12.
    # A solver override preserves the exact same mathematical formulation.
    solver=solver or ('gurobi' if free and sc=='restored' else 'highs')
    if solver=='gurobi':
        options={'Threads':4,'MIPGap':.0001,'TimeLimit':3600,'LogToConsole':0,'LogFile':str(folder/'solver.log')}
    else:
        options={'threads':4,'mip_rel_gap':.0001,'time_limit':3600,'log_to_console':False,'log_file':str(folder/'solver.log')}
        options['mip_lp_solver' if free else 'solver']='simplex'
    status,term=n.optimize(solver_name=solver,extra_functionality=extra,solver_options=options)
    if (status,term)!=('ok','optimal'):raise RuntimeError((folder.name,status,term))
    y=n.model.variables['grid_choice'].solution.to_series();rows=[]
    for z in gez.itertuples():
        zid=z.zone_id;isgrid=y[zid]>.5
        pv=n.generators.at['pv_'+zid,'p_nom_opt']*1000;batt=n.stores.at['store_'+zid,'e_nom_opt']*1000;conv=n.links.at['charge_'+zid,'p_nom_opt']*1000
        cost=fixed[zid]+pv*unit['pv']+batt*unit['battery']+conv*unit['converter'] if isgrid else off.at[zid,'local_EAC_USD']
        rows.append(dict(zone_id=zid,mode='grid' if isgrid else off.at[zid,'mode'],baseline_mode=selected.at[zid,'mode'],connections=z.connections,target_MWh=z.target_MWh,pv_kWp=pv if isgrid else off.at[zid,'pv_kWp'],battery_nominal_kWh=batt if isgrid else off.at[zid,'battery_nominal_kWh'],converter_AC_kW=conv if isgrid else off.at[zid,'converter_AC_kW'],local_annual_cost_USD=cost,grid_import_MWh=n.links_t.p0['import_'+zid].sum(),offgrid_key='' if isgrid else off.at[zid,'key']))
    choices=pd.DataFrame(rows);national=float((n.generators_t.p.sum()*n.generators.marginal_cost).sum());cost=constant+choices.local_annual_cost_USD.sum()+national
    penalty=float(n.links_t.p0.loc[:,n.links_t.p0.columns.str.startswith('charge_')].sum().sum()*.001)
    assert abs(cost+penalty-n.objective)<1,(cost,penalty,n.objective)
    if solver=='gurobi':
        solver_model=n.model.solver_model
        gap=float(solver_model.MIPGap) if free else 0.
        penalized_bound=float(solver_model.ObjBound) if free else float(n.objective)
    else:
        info=n.model.solver_model.getInfo();gap=float(info.mip_gap) if free else 0.
        penalized_bound=float(info.mip_dual_bound) if free else float(n.objective)
    # Penalized objective bound minus the maximum possible cycling penalty bounds the resource optimum.
    penalty_upper=sum(l['converter'] for l in limits.values())*8760*.001
    bound=penalized_bound-penalty_upper
    summary=dict(case=folder.name,solver=solver,solver_options=options,scenario=sc,free_service_choice=free,annual_system_cost_USD=float(cost),baseline_annual_system_cost_USD=old['annual_system_cost_USD'],annual_cost_saving_USD=float(old['annual_system_cost_USD']-cost),gezira_local_annual_cost_USD=float(choices.local_annual_cost_USD.sum()),outside_local_annual_cost_USD=float(others.local_EAC_USD.sum()),national_operating_cost_USD=national,annual_repair_cost_USD=old['annual_repair_cost_USD'],grid_connections=int(choices.loc[choices['mode'].eq('grid'),'connections'].sum()),potential_connections=int(gez.connections.sum()),grid_import_MWh=float(choices.grid_import_MWh.sum()),mip_gap=gap,resource_cost_lower_bound_USD=float(bound),cycling_tiebreak_USD=penalty,hours=8760,scope='Gezira joint grid/PV/battery capacities and dispatch; other regional choices and repairs fixed at section 13; independent off-grid columns retained')
    assert cost<=old['annual_system_cost_USD']+max(1,old['annual_system_cost_USD']*.0001),'Reference design should remain feasible'
    choices.to_csv(folder/'choices.csv',index=False);repairs.to_csv(folder/'fixed_repairs.csv');others.to_csv(folder/'fixed_other_zones.csv');budgets.to_csv(folder/'hydro_budgets.csv',index=False)
    n.export_to_netcdf(folder/'network.nc');(folder/'summary.json').write_text(json.dumps(summary,indent=2))
    del n;gc.collect()
    marker.write_text(json.dumps(dict(inputs=fp,outputs={p.name:lib.r.sha(p) for p in folder.iterdir() if p.is_file() and p.name!='manifest.json'}),indent=2))
    print('DONE',summary,flush=True);return summary

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--scenario',choices=['selective','restored']);p.add_argument('--solver',choices=['highs','gurobi']);a=p.parse_args()
    for sc in [a.scenario] if a.scenario else ['selective','restored']:
        solve(sc,False,a.solver);solve(sc,True,a.solver)
