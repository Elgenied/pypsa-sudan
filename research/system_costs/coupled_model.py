"""Full-year settlement investment coupled to national dispatch by valid cost cuts.

The national LP supplies supporting hyperplanes for its incremental dispatch cost.
The local MIP gives a lower bound; national re-dispatch gives a feasible upper bound.
Only certified solutions are marked complete. Scope is the declared candidate graph.
"""
from pathlib import Path
from contextlib import contextmanager
import argparse, copy, json, hashlib, time
import numpy as np
import pandas as pd
import pypsa
import pilot_model as pilot
import recovery_model as recovery
from cost_model import annuity

ROOT=pilot.ROOT;DATA=ROOT/'data/national_coupling'
OUT=Path(__file__).resolve().parent/'results/national_coupling'
CONFIG=json.loads((DATA/'config.json').read_text())
BASE=copy.deepcopy(recovery.BASE)
sha=recovery.sha

def fingerprints():
    files=list(DATA.glob('*'))+list((ROOT/'data/system_costs').glob('*.csv'))
    files += [Path(__file__),Path(__file__).with_name('pilot_model.py'),Path(__file__).with_name('cost_model.py'),Path(__file__).with_name('recovery_model.py'),ROOT/'data/electrification_pilot/config.json',ROOT/'data/recovery_planning/config.json']
    return {p.relative_to(ROOT).as_posix():sha(p) for p in sorted(files) if p.is_file()}

@contextmanager
def context():
    old=pilot.CONFIG,pilot.DATA,pilot.OUT,pilot.load_inputs
    pilot.CONFIG=copy.deepcopy(BASE);pilot.CONFIG['daily_kWh_per_service_point']=CONFIG['daily_kWh_per_connection']
    pilot.DATA=DATA;pilot.OUT=OUT/'offgrid';pilot.load_inputs=recovery.inputs
    try:yield
    finally:pilot.CONFIG,pilot.DATA,pilot.OUT,pilot.load_inputs=old

def setup():
    return pd.read_csv(DATA/'sites.csv'),pd.read_csv(DATA/'candidate_routes.csv')

def infrastructure_cost(component,quantity=1,repair_km=0):
    old=recovery.CONFIG
    recovery.CONFIG=CONFIG
    try:return recovery.infrastructure_cost(component,quantity,repair_km)
    finally:recovery.CONFIG=old

def valid(folder):
    marker=folder/'manifest.json'
    if not marker.exists():return False
    m=json.loads(marker.read_text())
    return m.get('inputs')==fingerprints() and all((folder/p).is_file() and sha(folder/p)==h for p,h in m['outputs'].items())

def stamp(folder,files):
    (folder/'manifest.json').write_text(json.dumps(dict(inputs=fingerprints(),outputs={p.relative_to(folder).as_posix():sha(p) for p in files}),indent=2)+'\n')

def offgrid(sites):
    folder=OUT/'offgrid';folder.mkdir(parents=True,exist_ok=True)
    if not valid(folder):
        rows=[]
        with context():
            for site in sites.itertuples(index=False):
                for mode in ['standalone','mini_grid']:
                    record,_,_=pilot.solve(site,mode);record['site_id']=site.site_id;rows.append(record)
        pd.DataFrame(rows).to_csv(folder/'summary.csv',index=False,lineterminator='\n')
        stamp(folder,[folder/'summary.csv',*folder.glob('*hourly.csv.gz')])
    return pd.read_csv(folder/'summary.csv')

def national_network(extra_import):
    n=pypsa.Network(DATA/'national_reference.nc')
    n.remove('Generator',n.generators.index[n.generators.carrier.eq('shortage')])
    # The old reference clock is local; the weather/access clock is UTC.
    n.loads_t.p_set=pd.DataFrame(np.roll(n.loads_t.p_set.to_numpy(),-2,axis=0),index=n.snapshots,columns=n.loads_t.p_set.columns)
    n.add('Load','additional_access',bus=CONFIG['national_bus'],p_set=np.asarray(extra_import))
    facts=pd.read_csv(DATA/'national_2022.csv',index_col=0).value
    hydro_energy=facts.gross_hydro/(facts.gross_hydro+facts.gross_combustible+facts.gross_other)*facts.net_generation*1000
    n.generators['e_sum_max']=np.inf
    hydro=n.generators.carrier.eq('hydro')
    n.generators.loc[hydro,'e_sum_max']=hydro_energy*n.generators.loc[hydro,'p_nom']/facts.capacity_hydro
    n.meta=dict(scope='National reference dispatch for incremental settlement service',time_basis='UTC; periodic shift of synthetic local-year load',no_shortage_allowed=True)
    return n

def national_solve(imports,folder):
    folder.mkdir(parents=True,exist_ok=True)
    n=national_network(imports)
    status,term=n.optimize(solver_name='highs',solver_options={'threads':4,'solver':'ipm','run_crossover':'off','ipm_optimality_tolerance':1e-9,'log_to_console':False})
    if (status,term)!=('ok','optimal'):raise RuntimeError(f'National dispatch {status}/{term}; no feasible coupled result claimed')
    cost=float((n.generators_t.p.sum()*n.generators.marginal_cost).sum())
    if abs(cost-n.objective)>.1:raise AssertionError('National objective accounting')
    price=n.buses_t.marginal_price[CONFIG['national_bus']].copy()
    pd.DataFrame(dict(import_MW=np.asarray(imports),price_USD_MWh=price)).to_csv(folder/'interface.csv.gz',index_label='time_UTC',compression={'method':'gzip','mtime':0},lineterminator='\n')
    n.export_to_netcdf(folder/'network.nc')
    energy=n.generators_t.p.sum().groupby(n.generators.carrier).sum()
    energy.rename('MWh').to_csv(folder/'generation.csv',lineterminator='\n')
    info=n.model.solver_model.getInfo()
    (folder/'summary.json').write_text(json.dumps(dict(cost_USD=cost,objective_USD=float(n.objective),status=term,imports_to_access_MWh=float(np.sum(imports)),hydro_budget_MWh=float(n.generators.loc[n.generators.carrier.eq('hydro'),'e_sum_max'].sum()),max_primal_infeasibility=float(info.max_primal_infeasibility),max_dual_infeasibility=float(info.max_dual_infeasibility)),indent=2)+'\n')
    stamp(folder,[folder/'network.nc',folder/'interface.csv.gz',folder/'generation.csv',folder/'summary.json'])
    return cost,price

def national_base():
    folder=OUT/'national_base'
    if valid(folder):
        s=json.loads((folder/'summary.json').read_text());h=pd.read_csv(folder/'interface.csv.gz',index_col=0,parse_dates=True)
        return s['cost_USD'],h.price_USD_MWh
    return national_solve(np.zeros(8760),folder)

def local_build(scenario,off,cuts):
    sites,routes=setup();sc=CONFIG['scenarios'][scenario]
    profiles={};packages={};params={k:float(v['central']) for k,v in recovery.inputs()[1].items()}
    with context():
        for s in sites.itertuples(index=False):
            _,cf,load=pilot.weather_and_load(s);profiles[s.site_id]=(cf,load)
            _,q,ledger,_,unit,groups=pilot.cost_context(s,'grid_extension')
            q['mv_line']=0;q['fuel_tank_ats']=1 if s.site_id=='S1' else 0
            q['transformer_100kVA']=max(1,np.ceil(load.max()/(.08*(1-BASE['grid_distribution_loss']))))
            packages[s.site_id]=dict(q=q,ledger=ledger,unit=unit,groups=groups,fixed=recovery.fixed_eac(ledger(q)))
    best=off.sort_values('equivalent_annual_cost_USD').drop_duplicates('site_id').set_index('site_id')
    sns=profiles['S1'][0].index
    available=pd.Series((~((sns.hour+2)%24).isin(sc['outage_local_hours'])).astype(float),index=sns)
    n=pypsa.Network();n.set_snapshots(sns)
    n.add('Carrier',['electricity','solar','diesel','battery','portfolio','national_interface'])
    n.add('Bus','upstream',carrier='electricity');n.add('Bus','battery',carrier='battery')
    n.add('Generator','national_import',bus='upstream',carrier='national_interface',p_nom=CONFIG['common_feeder_capacity_MW'],p_max_pu=available)
    for s in sites.itertuples(index=False):
        sid=s.site_id;load=profiles[sid][1]/(1-BASE['grid_distribution_loss'])
        n.add('Bus',sid,carrier='electricity',x=s.lon,y=s.lat)
        n.add('Load',sid+'_grid_equivalent',bus=sid,p_set=load)
        # An accounting column cancels this load exactly when the site is off-grid.
        # Its actual off-grid service, losses and assets are in the independent design.
        n.add('Generator',sid+'_offgrid_column',bus=sid,carrier='portfolio',p_nom=float(load.max()))
    count=float(sites.num_connections.sum());u=packages['S1']['unit']
    n.add('Generator','hub_pv',bus='S1',carrier='solar',p_nom_extendable=True,p_nom_max=count*BASE['pv_capacity_limit_kWp_per_service_point']/1000,p_max_pu=profiles['S1'][0],capital_cost=u['pv']*1000)
    fuel_mc=(params['diesel_delivered_price']*params['diesel_specific_fuel']+params['diesel_variable_om'])*1000
    n.add('Generator','hub_diesel',bus='S1',carrier='diesel',p_nom_extendable=True,p_nom_max=count*BASE['diesel_limit_kW_per_service_point']/1000,capital_cost=u['diesel']*1000,marginal_cost=fuel_mc)
    n.add('Store','hub_battery',bus='battery',carrier='battery',e_nom_extendable=True,e_nom_max=count*BASE['battery_limit_kWh_per_service_point']/1000,e_min_pu=BASE['battery_min_soc'],e_max_pu=BASE['battery_max_soc'],e_cyclic=True,capital_cost=u['battery']*1000)
    n.add('Link','charge',bus0='S1',bus1='battery',efficiency=BASE['battery_charge_efficiency'],p_nom_extendable=True,p_nom_max=count*BASE['converter_limit_kW_per_service_point']/1000,capital_cost=u['converter']*1000,marginal_cost=.001)
    n.add('Link','discharge',bus0='battery',bus1='S1',efficiency=BASE['battery_discharge_efficiency'],p_nom_extendable=True,p_nom_max=count*BASE['converter_limit_kW_per_service_point']/1000/BASE['battery_discharge_efficiency'])
    n.add('Link','common_feeder',bus0='upstream',bus1='S1',efficiency=CONFIG['common_feeder_efficiency'],p_nom=CONFIG['common_feeder_capacity_MW'])
    for e in routes.itertuples(index=False):
        for suffix,a,b in [('f',e.from_site,e.to_site),('r',e.to_site,e.from_site)]:n.add('Link',e.edge_id+'_'+suffix,bus0=a,bus1=b,p_nom=e.capacity_MW,efficiency=e.efficiency)
    route_cost={e.edge_id:infrastructure_cost('mv_line',e.route_km) for e in routes.itertuples(index=False)}
    repair=infrastructure_cost('mv_line',repair_km=CONFIG['common_feeder_repair_km'])
    def extra(network,snapshots):
        m=network.model;z=m.add_variables(binary=True,coords=[pd.Index(sites.site_id,name='site')],name='grid_choice')
        y=m.add_variables(binary=True,coords=[pd.Index(routes.edge_id,name='edge')],name='route_build')
        r=m.add_variables(binary=True,name='repair_feeder')
        p=m.variables['Generator-p'];f=m.variables['Link-p'];gp=m.variables['Generator-p_nom'];lp=m.variables['Link-p_nom'];se=m.variables['Store-e_nom']
        for sid in sites.site_id:
            load=(profiles[sid][1]/(1-BASE['grid_distribution_loss'])).rename_axis('snapshot').to_xarray()
            m.add_constraints(p.sel(name=sid+'_offgrid_column')==load*(1-z.sel(site=sid)),name=sid+'_column_service')
            m.add_constraints(z.sel(site=sid)<=r,name=sid+'_requires_feeder')
        m.add_constraints(r==z.sel(site='S1'),name='hub_requires_root_service')
        m.add_constraints(r*repair['initial']<=sc['repair_budget_USD'],name='repair_budget')
        m.add_constraints(f.sel(name='common_feeder')<=CONFIG['common_feeder_capacity_MW']*r,name='feeder_activation')
        for g in ['hub_pv','hub_diesel']:m.add_constraints(gp.sel(name=g)<=n.generators.at[g,'p_nom_max']*r,name=g+'_activate')
        m.add_constraints(se.sel(name='hub_battery')<=n.stores.at['hub_battery','e_nom_max']*r,name='storage_activate')
        m.add_constraints(lp.sel(name='charge')<=n.links.at['charge','p_nom_max']*r,name='converter_activate')
        m.add_constraints(lp.sel(name='charge')==BASE['battery_discharge_efficiency']*lp.sel(name='discharge'),name='converter_rating')
        m.add_constraints(f.sel(name='charge')+BASE['battery_discharge_efficiency']*f.sel(name='discharge')<=lp.sel(name='charge'),name='converter_throughput')
        m.add_constraints(p.sel(name='hub_diesel').sum()<=sum(profiles[sid][1].sum()*BASE['diesel_max_fraction_of_delivered_energy']*z.sel(site=sid) for sid in sites.site_id),name='diesel_energy')
        commodity=m.add_variables(lower=0,coords=[pd.Index([e+'_'+d for e in routes.edge_id for d in ['f','r']],name='arc')],name='connectivity_flow')
        for e in routes.itertuples(index=False):
            m.add_constraints(y.sel(edge=e.edge_id)<=r,name=e.edge_id+'_root')
            m.add_constraints(f.sel(name=e.edge_id+'_f')+f.sel(name=e.edge_id+'_r')<=e.capacity_MW*y.sel(edge=e.edge_id),name=e.edge_id+'_capacity')
            for d in ['f','r']:m.add_constraints(commodity.sel(arc=e.edge_id+'_'+d)<=len(sites)*y.sel(edge=e.edge_id),name=e.edge_id+'_'+d+'_commodity')
        for sid in sites.site_id:
            balance=z.sum() if sid=='S1' else 0
            incident=[]
            for e in routes.itertuples(index=False):
                if e.from_site==sid:balance+=commodity.sel(arc=e.edge_id+'_r')-commodity.sel(arc=e.edge_id+'_f');incident.append(e.edge_id)
                if e.to_site==sid:balance+=commodity.sel(arc=e.edge_id+'_f')-commodity.sel(arc=e.edge_id+'_r');incident.append(e.edge_id)
            m.add_constraints(balance==z.sel(site=sid),name=sid+'_connectivity')
            if sid!='S1':m.add_constraints(sum(y.sel(edge=e) for e in incident)>=z.sel(site=sid),name=sid+'_incident_cut')
        theta=m.add_variables(lower=-np.inf,name='national_incremental_cost')
        for i,cut in enumerate(cuts):
            price=pd.Series(cut['price'],index=sns).rename_axis('snapshot').to_xarray()
            rhs=cut['cost_delta']-float(np.dot(cut['price'],cut['imports']))+(p.sel(name='national_import')*price).sum()
            m.add_constraints(theta>=rhs,name=f'national_support_{i}')
        # Linopy requires a variable expression rather than a literal objective constant.
        one=m.add_variables(lower=1,upper=1,name='accounting_one')
        fixed=sum(float(best.at[sid,'equivalent_annual_cost_USD'])*(one-z.sel(site=sid))+packages[sid]['fixed']*z.sel(site=sid) for sid in sites.site_id)
        m.objective+=fixed+sum(route_cost[e]['eac']*y.sel(edge=e) for e in routes.edge_id)+repair['eac']*r+theta
    return n,extra,dict(sites=sites,routes=routes,profiles=profiles,packages=packages,best=best,route_cost=route_cost,repair=repair,params=params,availability=available)

def solve_master(scenario,off,cuts,folder):
    folder.mkdir(parents=True,exist_ok=True);n,extra,ctx=local_build(scenario,off,cuts)
    (folder/'solver.log').write_text('')
    status,term=n.optimize(solver_name='highs',extra_functionality=extra,solver_options={'threads':4,'mip_lp_solver':'ipm','mip_rel_gap':CONFIG['master_mip_gap'],'time_limit':1200,'log_to_console':False,'log_file':str(folder/'solver.log')})
    if (status,term)!=('ok','optimal'):raise RuntimeError(f'Local master {scenario}: {status}/{term}; no complete solution published')
    info=n.model.solver_model.getInfo()
    n.export_to_netcdf(folder/'local_network.nc')
    for key in ['grid_choice','route_build','connectivity_flow']:n.model.variables[key].solution.to_series().rename('value').to_csv(folder/(key+'.csv'),lineterminator='\n')
    repair=float(n.model.variables['repair_feeder'].solution.item());theta=float(n.model.variables['national_incremental_cost'].solution.item())
    penalty=float(n.links_t.p0.charge.sum()*.001)
    meta=dict(objective=float(n.objective),lower_bound=float(info.mip_dual_bound),mip_gap=float(info.mip_gap),repair=repair,national_cost_estimate=theta,charge_penalty=penalty)
    (folder/'master.json').write_text(json.dumps(meta,indent=2)+'\n')
    return n,ctx,meta

def summarize(scenario,folder,n,ctx,meta,national_delta,lower,upper,iterations):
    z=pd.read_csv(folder/'grid_choice.csv',index_col=0).value;y=pd.read_csv(folder/'route_build.csv',index_col=0).value
    caps=dict(pv_kWp=max(0,n.generators.at['hub_pv','p_nom_opt']*1000),diesel_kW=max(0,n.generators.at['hub_diesel','p_nom_opt']*1000),battery_nominal_kWh=max(0,n.stores.at['hub_battery','e_nom_opt']*1000),converter_AC_kW=max(0,n.links.at['charge','p_nom_opt']*1000))
    rows=[]
    for s in ctx['sites'].itertuples(index=False):
        sid=s.site_id
        if z[sid]>.5:
            package=ctx['packages'][sid];q=dict(package['q']);c=caps if sid=='S1' else {k:0. for k in caps}
            for a,key in [('pv','pv_kWp'),('diesel','diesel_kW'),('battery','battery_nominal_kWh'),('converter','converter_AC_kW')]:
                for item in package['groups'][a]:q[item]=c[key]
            ledger=package['ledger'](q);cost=recovery.fixed_eac(ledger)
            if sid=='S1':cost+=n.generators_t.p.hub_diesel.sum()*n.generators.at['hub_diesel','marginal_cost']
            initial=ledger['summary']['initial_budget_USD'];mode='grid'
        else:
            o=ctx['best'].loc[sid];c={k:float(o[k]) for k in caps};cost=o.equivalent_annual_cost_USD;initial=o.initial_budget_USD;mode=o['mode']
        rows.append(dict(scenario=scenario,site_id=sid,geohash=s.geohash,source_name=s.village_name,connections=s.num_connections,choice=mode,local_EAC_USD=float(cost),initial_USD=float(initial),**c))
    table=pd.DataFrame(rows);table.to_csv(folder/'settlements.csv',index=False,lineterminator='\n')
    shared=sum(ctx['route_cost'][e]['eac']*y[e] for e in y.index)+ctx['repair']['eac']*meta['repair']
    initial_shared=sum(ctx['route_cost'][e]['initial']*y[e] for e in y.index)+ctx['repair']['initial']*meta['repair']
    eac=float(table.local_EAC_USD.sum()+shared+national_delta)
    if abs(eac-(upper-meta['charge_penalty']))>.2:raise AssertionError('Coupled cost accounting mismatch')
    result=dict(scenario=scenario,equivalent_annual_access_cost_USD=eac,lifecycle_access_NPC_USD=eac/annuity(ctx['params']['real_discount_rate'],ctx['params']['horizon_years']),initial_local_investment_USD=float(table.initial_USD.sum()+initial_shared),
        incremental_national_dispatch_cost_USD=float(national_delta),shared_EAC_USD=float(shared),repair_spend_USD=float(ctx['repair']['initial']*meta['repair']),national_import_MWh=float(n.generators_t.p.national_import.sum()),
        lower_bound_USD=float(lower),feasible_upper_bound_USD=float(upper),certified_absolute_gap_USD=max(0,float(upper-lower)),certified_relative_gap=max(0,float((upper-lower)/upper)),iterations=iterations,
        numerical_charge_penalty_USD=meta['charge_penalty'],delivered_MWh=float(sum(p[1].sum() for p in ctx['profiles'].values())),new_route_km=float(sum(e.route_km*y[e.edge_id] for e in ctx['routes'].itertuples())),
        **{mode+'_connections':int(table.loc[table.choice==mode,'connections'].sum()) for mode in ['grid','mini_grid','standalone']})
    (folder/'summary.json').write_text(json.dumps(result,indent=2)+'\n');return result

def coupled_case(scenario,off,base_cost,base_price):
    folder=OUT/scenario
    if valid(folder):return json.loads((folder/'summary.json').read_text())
    cuts=[dict(imports=np.zeros(8760),price=np.asarray(base_price),cost_delta=0.)];history=[];best_upper=np.inf;best=None;lower=-np.inf
    for i in range(CONFIG['maximum_iterations']):
        iteration=folder/f'iteration_{i:02d}'
        print(f'Coupling {scenario}, iteration {i+1}',flush=True)
        n,ctx,meta=solve_master(scenario,off,cuts,iteration)
        imports=n.generators_t.p.national_import.to_numpy()
        national_cost,prices=national_solve(imports,iteration/'national')
        delta=national_cost-base_cost;upper=meta['objective']-meta['national_cost_estimate']+delta
        lower=max(lower,meta['lower_bound'])
        if upper<best_upper:best_upper=upper;best=(iteration,n,ctx,meta,delta)
        # A valid lower bound may exceed the upper by only numerical LP/MIP tolerances.
        if lower>best_upper+.5:raise AssertionError('Invalid coupling lower bound')
        gap=max(0,best_upper-lower)
        history.append(dict(iteration=i+1,master_objective=meta['objective'],master_lower_bound=meta['lower_bound'],national_delta_USD=delta,national_estimate_USD=meta['national_cost_estimate'],candidate_upper_bound=upper,best_upper_bound=best_upper,lower_bound=lower,gap_USD=gap,relative_gap=gap/max(1,abs(best_upper))))
        pd.DataFrame(history).to_csv(folder/'convergence.csv',index=False,lineterminator='\n')
        print(f'{scenario}: coupling gap ${gap:.4f}; imports {imports.sum():.3f} MWh',flush=True)
        if gap<=max(CONFIG['coupling_absolute_tolerance_USD'],CONFIG['coupling_relative_tolerance']*abs(best_upper)):
            chosen,n,ctx,meta,delta=best
            result=summarize(scenario,chosen,n,ctx,meta,delta,lower,best_upper,len(history))
            result['selected_iteration']=chosen.name
            (folder/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
            # Retain support vectors so the bound construction is auditable.
            pd.DataFrame({f'price_{j}':c['price'] for j,c in enumerate(cuts)}).to_csv(folder/'cut_prices.csv.gz',index=False,compression={'method':'gzip','mtime':0},lineterminator='\n')
            pd.DataFrame({f'import_{j}':c['imports'] for j,c in enumerate(cuts)}).to_csv(folder/'cut_imports.csv.gz',index=False,compression={'method':'gzip','mtime':0},lineterminator='\n')
            (folder/'cuts.json').write_text(json.dumps([dict(cost_delta=c['cost_delta'],intercept=c['cost_delta']-float(np.dot(c['price'],c['imports']))) for c in cuts],indent=2)+'\n')
            stamp(folder,[p for p in folder.rglob('*') if p.is_file() and p.name!='manifest.json'])
            return result
        cuts.append(dict(imports=imports,price=np.asarray(prices),cost_delta=delta))
    raise RuntimeError(f'{scenario}: coupling tolerance not reached; incomplete, inspect convergence.csv')

def run():
    OUT.mkdir(parents=True,exist_ok=True)
    if valid(OUT):return pd.read_csv(OUT/'summary.csv')
    sites,_=setup();off=offgrid(sites);base_cost,base_price=national_base()
    rows=[coupled_case(sc,off,base_cost,base_price) for sc in CONFIG['scenario_order']]
    summary=pd.DataFrame(rows);summary.to_csv(OUT/'summary.csv',index=False,lineterminator='\n')
    stamp(OUT,[p for p in OUT.rglob('*') if p.is_file() and p.name!='manifest.json'])
    return summary

if __name__=='__main__':run()
