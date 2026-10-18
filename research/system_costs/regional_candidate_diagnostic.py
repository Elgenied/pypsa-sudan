"""Nested grid portfolios: isolate the effect of removing designs as recovery improves.

Uses existing checked hourly designs, retaining every baseline candidate. No new
weather, demand, costs, asset capacities, or damage assumptions are introduced.
"""
from pathlib import Path
import argparse,json,gc
import numpy as np
import pandas as pd
import regional_model as base
from check_coupled import load_network,electrical_checks,TOL

lib=base.lib
OUT=Path(__file__).resolve().parent/'results/regional_candidate_diagnostic'
ORDER=['restricted','selective','restored']

def candidates(scenario,expanded=True):
    library=pd.read_csv(lib.OUT/'summary.csv');zones=lib.zones(36)
    sources=ORDER[:ORDER.index(scenario)+1] if expanded else [scenario]
    rows=[]
    for z in zones.itertuples():
        for mode in ['standalone','mini_grid']:
            q=lib.package(z,mode,scenario,library);q['design_scenario']='offgrid';rows.append(q)
        for source in sources:
            q=lib.package(z,'grid',source,library);q['design_scenario']=source;rows.append(q)
    return zones,library,pd.DataFrame(rows)

def fingerprint(scenario,expanded,force_gezira,fixed):
    return dict(base=base.fingerprints(),script=lib.r.sha(Path(__file__)),library_manifest=lib.r.sha(lib.OUT/'manifest.json'),scenario=scenario,expanded=expanded,force_gezira=force_gezira,fixed=fixed)

def solve(scenario,expanded=True,force_gezira=False,fixed=False):
    name=scenario+('_expanded' if expanded else '_baseline')+('_gezira_grid' if force_gezira else '')+('_fixed' if fixed else '')
    folder=OUT/name;folder.mkdir(parents=True,exist_ok=True)
    fp=fingerprint(scenario,expanded,force_gezira,fixed)
    marker=folder/'manifest.json'
    if marker.exists():
        old=json.loads(marker.read_text())
        if old['inputs']==fp and all(lib.r.sha(folder/f)==h for f,h in old['outputs'].items()):return json.loads((folder/'summary.json').read_text())
    zones,library,opts=candidates(scenario,expanded)
    off=opts[opts['mode'].ne('grid')].sort_values(['local_EAC_USD','mode']).drop_duplicates('zone_id').set_index('zone_id')
    grids=opts[opts['mode'].eq('grid')].set_index('key')
    n=base.coupled.national_network(np.zeros(8760));n.remove('Load','additional_access');n.add('Carrier','portfolio_accounting')
    for bus in zones.supply_bus.unique():
        for suffix in [' consumption',' losses']:n.loads_t.p_set[bus+suffix]*=1-base.CONFIG['residential_share']
    repairs=pd.read_csv(base.DATA/'corridor_register.csv').set_index('asset_id');projects=repairs[repairs.candidate_repair].copy()
    for name,r in repairs.iterrows():n.links.at[name,'p_nom']=r.reference_MW
    budgets=base.monthly_budgets(n)
    params={k:float(v['central']) for k,v in lib.inputs()[1].items()}
    annual_factor=base.annuity(params['real_discount_rate'],base.CONFIG['repair_life_years'])+base.CONFIG['repair_annual_om_fraction']
    service={};profiles={};peaks={};catalog=library.set_index('key')
    hours=base.CONFIG['scenarios'][scenario]['outage_local_hours']
    for key,g in grids.iterrows():
        h=pd.read_csv(lib.OUT/catalog.at[key,'hourly_file'],index_col=0,parse_dates=True)
        if hours:assert h.loc[((h.index.hour+2)%24).isin(hours),'grid_MW'].abs().max()<TOL,(key,scenario)
        series=pd.Series(h.grid_MW.to_numpy()*g.scale,index=n.snapshots)
        profiles[key]=series;peaks[key]=float(series.max())
        assert peaks[key]>0
        service[g.supply_bus]=service.get(g.supply_bus,0.)+series
        n.add('Generator','cancel_'+key,bus=g.supply_bus,carrier='portfolio_accounting',p_nom_extendable=True,p_nom_max=peaks[key],p_max_pu=series/peaks[key],p_min_pu=series/peaks[key])
    for bus,series in service.items():n.add('Load','service_'+bus,bus=bus,p_set=series)
    oldfolder=base.OUT/f'{scenario}_mixed_36_d1_f1'
    oldchoices=pd.read_csv(oldfolder/'zone_choices.csv').set_index('zone_id')
    oldrepairs=pd.read_csv(oldfolder/'repairs.csv').set_index('asset_id')
    def extra(network,sns):
        m=network.model;one=m.add_variables(lower=1,upper=1,name='constant_one')
        if fixed:
            y=m.add_variables(lower=0,upper=1,coords=[pd.Index(grids.index,name='candidate')],name='candidate_choice')
            r=m.add_variables(lower=0,upper=1,coords=[pd.Index(projects.index,name='project')],name='corridor_repair')
        else:
            y=m.add_variables(binary=True,coords=[pd.Index(grids.index,name='candidate')],name='candidate_choice')
            r=m.add_variables(binary=True,coords=[pd.Index(projects.index,name='project')],name='corridor_repair')
        for z in zones.itertuples():
            keys=grids.index[grids.zone_id.eq(z.zone_id)];selected=y.sel(candidate=keys).sum()
            m.add_constraints(selected<=1,name=z.zone_id+'_one_option')
            if force_gezira and z.state=='Gezira':m.add_constraints(selected==1,name=z.zone_id+'_forced_grid')
            if fixed:
                for key in keys:m.add_constraints(y.sel(candidate=key)==int(oldchoices.at[z.zone_id,'key']==key),name='fixed_'+key)
        if fixed:
            for name in projects.index:m.add_constraints(r.sel(project=name)==oldrepairs.at[name,'selected'],name='fixed_repair_'+name)
        if base.CONFIG['scenarios'][scenario]['force_repairs']:m.add_constraints(r==1,name='restored_backbone')
        spend=sum(projects.at[e,'repair_initial_USD']*r.sel(project=e) for e in projects.index)
        m.add_constraints(spend<=base.CONFIG['scenarios'][scenario]['repair_budget_USD'],name='repair_budget')
        for name,e in projects.iterrows():
            limit=e.reference_MW*(e.available_fraction+(1-e.available_fraction)*r.sel(project=name))
            m.add_constraints(m.variables['Link-p'].sel(name=name)<=limit,name=name+'_upper')
            m.add_constraints(m.variables['Link-p'].sel(name=name)>=-limit,name=name+'_lower')
        for key,g in grids.iterrows():m.add_constraints(m.variables['Generator-p_nom'].sel(name='cancel_'+key)==peaks[key]*(one-y.sel(candidate=key)),name='profile_'+key)
        for b in budgets.itertuples():m.add_constraints(m.variables['Generator-p'].sel(name=b.generator,snapshot=sns[sns.month==b.month]).sum()<=b.budget_MWh,name=b.generator.replace(' ','_')+f'_m{b.month}')
        local=off.local_EAC_USD.sum()*one+sum((g.local_EAC_USD-off.at[g.zone_id,'local_EAC_USD'])*y.sel(candidate=key) for key,g in grids.iterrows())
        m.objective+=local+spend*annual_factor
    print('SOLVE',folder.name,flush=True)
    status,term=n.optimize(solver_name='highs',extra_functionality=extra,solver_options={'threads':4,'mip_lp_solver':'ipm','mip_rel_gap':.0001,'time_limit':1800,'log_to_console':False,'log_file':str(folder/'solver.log')})
    if (status,term)!=('ok','optimal'):raise RuntimeError((folder.name,status,term))
    y=n.model.variables['candidate_choice'].solution.to_series();r=n.model.variables['corridor_repair'].solution.to_series()
    selected=[]
    for z in zones.itertuples():
        keys=grids.index[grids.zone_id.eq(z.zone_id)&grids.index.isin(y[y>.5].index)]
        assert len(keys)<=1
        selected.append(grids.loc[keys[0]].to_dict()|{'key':keys[0]} if len(keys) else off.loc[z.zone_id].to_dict()|{'zone_id':z.zone_id})
    chosen=pd.DataFrame(selected);chosen['zone_id']=zones.zone_id.to_numpy()
    national=float((n.generators_t.p.sum()*n.generators.marginal_cost).sum());repair_cost=float((projects.repair_initial_USD*r).sum()*annual_factor)
    cost=float(chosen.local_EAC_USD.sum()+national+repair_cost)
    assert abs(cost-n.objective)<1
    info=n.model.solver_model.getInfo()
    summary=dict(case=folder.name,scenario=scenario,expanded=expanded,force_gezira=force_gezira,fixed_choices=fixed,annual_system_cost_USD=cost,local_annual_cost_USD=float(chosen.local_EAC_USD.sum()),national_operating_cost_USD=national,annual_repair_cost_USD=repair_cost,grid_import_MWh=float(chosen.grid_import_MWh.sum()),grid_candidates=len(grids),offgrid_candidates=2*len(zones),hours=len(n.snapshots),mip_gap=0. if fixed else float(info.mip_gap),lower_bound_USD=cost if fixed else float(info.mip_dual_bound),gezira_grid_connections=int(chosen.loc[chosen.state.eq('Gezira')&chosen['mode'].eq('grid'),'connections'].sum()))
    opts.to_csv(folder/'options.csv',index=False);chosen.to_csv(folder/'zone_choices.csv',index=False)
    projects['selected']=r;projects.to_csv(folder/'repairs.csv');budgets.to_csv(folder/'hydro_budgets.csv',index=False)
    n.export_to_netcdf(folder/'network.nc');(folder/'summary.json').write_text(json.dumps(summary,indent=2))
    # Check exported hourly balances and actual (non-accounting) grid deliveries.
    del n;gc.collect();saved=load_network(folder/'network.nc');error=electrical_checks(saved)
    assert not saved.generators.carrier.isin(['shortage','unserved_diagnostic']).any()
    for bus in zones.supply_bus.unique():
        actual=saved.loads_t.p_set['service_'+bus]-saved.generators_t.p.loc[:,saved.generators.bus.eq(bus)&saved.generators.carrier.eq('portfolio_accounting')].sum(axis=1)
        expected=pd.Series(0.,index=saved.snapshots)
        for _,row in chosen.iterrows():
            if row['mode']=='grid' and row.supply_bus==bus:expected+=profiles[row.key]
        assert (actual-expected).abs().max()<TOL
    for b in budgets.itertuples():assert saved.generators_t.p.loc[saved.snapshots.month==b.month,b.generator].sum()<=b.budget_MWh+.1
    for name,p in projects.iterrows():assert saved.links_t.p0[name].abs().max()<=p.reference_MW*(p.available_fraction+(1-p.available_fraction)*p.selected)+TOL
    assert (projects.repair_initial_USD*projects.selected).sum()<=base.CONFIG['scenarios'][scenario]['repair_budget_USD']+.1
    if expanded and not force_gezira:
        old=json.loads((oldfolder/'summary.json').read_text())
        assert cost<=old['annual_system_cost_USD']+max(1,old['annual_system_cost_USD']*.0001),'Expanded feasible set worsened beyond solver tolerance'
    if fixed:assert abs(cost-json.loads((oldfolder/'summary.json').read_text())['annual_system_cost_USD'])<10,'Baseline formulation reproduction'
    validation=dict(passed=True,max_bus_balance_error_MW=error,hours=8760,no_unserved_generator=True,grid_availability_checked=True,objective_reconstructed=True,field_validated=False)
    (folder/'validation.json').write_text(json.dumps(validation,indent=2));del saved;gc.collect()
    files=[p for p in folder.iterdir() if p.is_file() and p.name!='manifest.json']
    marker.write_text(json.dumps(dict(inputs=fp,outputs={p.name:lib.r.sha(p) for p in files}),indent=2))
    print('DONE',summary,flush=True);return summary

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--case',choices=['baseline','selective','restored','forced']);args=parser.parse_args()
    if args.case=='baseline':solve('restored',False,fixed=True)
    elif args.case=='selective':solve('selective')
    elif args.case=='restored':solve('restored')
    elif args.case=='forced':solve('restored',force_gezira=True)
    else:
        solve('restored',False,fixed=True);solve('selective');solve('restored');solve('restored',force_gezira=True)
