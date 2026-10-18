"""Joint hourly recovery planning with binary service, route and repair decisions.

Off-grid systems are optimized independently and inserted as exact fixed-service
cost columns: they have no interaction with regional supply or other settlements.
Grid-connected PV/storage/backup, shared routes and upstream repairs are jointly
optimized over every hour of 2022. Export custom decisions separately from NetCDF.
"""
from pathlib import Path
from contextlib import contextmanager
import argparse,copy,hashlib,json,logging,itertools
import numpy as np
import pandas as pd
import pypsa
import pilot_model as pilot
from cost_model import annuity

ROOT=pilot.ROOT;DATA=ROOT/'data/recovery_planning';OUT=Path(__file__).resolve().parent/'results/recovery'
CONFIG=json.loads((DATA/'config.json').read_text())
BASE=copy.deepcopy(pilot.CONFIG)
MODES=['standalone','mini_grid','grid']
RAW_LOAD_INPUTS=pilot.load_inputs

def inputs():
    result=copy.deepcopy(RAW_LOAD_INPUTS())
    result[1]['nonrecoverable_tax']['central']='0'
    return result

@contextmanager
def context(output=None):
    old=pilot.CONFIG,pilot.DATA,pilot.OUT,pilot.load_inputs
    pilot.CONFIG=copy.deepcopy(BASE);pilot.CONFIG['daily_kWh_per_service_point']=CONFIG['daily_kWh_per_connection']
    pilot.DATA=DATA;pilot.OUT=output or OUT/'offgrid';pilot.load_inputs=inputs
    try:yield
    finally:pilot.CONFIG,pilot.DATA,pilot.OUT,pilot.load_inputs=old

def sha(p):
    raw=Path(p).read_bytes()
    return hashlib.sha256(raw if Path(p).suffix in ['.gz','.nc'] else raw.replace(b'\r\n',b'\n')).hexdigest()

def fingerprints():
    files=list(DATA.glob('*'))+list((ROOT/'data/system_costs').glob('*.csv'))
    files += [Path(__file__),Path(__file__).with_name('pilot_model.py'),Path(__file__).with_name('cost_model.py'),ROOT/'data/electrification_pilot/config.json']
    return {p.relative_to(ROOT).as_posix():sha(p) for p in sorted(files) if p.is_file()}

def fixed_eac(ledger):
    return ledger['summary']['equivalent_annual_cost_USD']-sum(ledger['operating'][k] for k in ['grid_supply','diesel_fuel','diesel_runtime_maintenance'])

def infrastructure_cost(component,quantity=1,repair_km=0):
    """Difference of full ledgers cancels site admin, energy and other baseline costs."""
    from cost_model import evaluate
    q={k:0. for k in inputs()[0]};q['house_wiring']=1
    design=dict(connections=1,daily_kWh_per_connection=1,diesel_generation_fraction=0,repair_mv_route_km=0,repair_cost_fraction=0)
    a=evaluate('grid_extension',inputs=inputs(),quantity_overrides=q,design_overrides=design)
    if repair_km:design.update(repair_mv_route_km=repair_km,repair_cost_fraction=CONFIG['repair_fraction_of_new_line'])
    else:q[component]+=quantity
    b=evaluate('grid_extension',inputs=inputs(),quantity_overrides=q,design_overrides=design)
    return dict(eac=fixed_eac(b)-fixed_eac(a),initial=b['summary']['initial_budget_USD']-a['summary']['initial_budget_USD'])

def setup():
    sites=pd.read_csv(DATA/'sites.csv');routes=pd.read_csv(DATA/'candidate_routes.csv')
    return sites,routes,{k:float(v['central']) for k,v in inputs()[1].items()}

def prepare_offgrid(sites):
    folder=OUT/'offgrid';folder.mkdir(parents=True,exist_ok=True);marker=folder/'manifest.json'
    current=fingerprints()
    if marker.exists():
        m=json.loads(marker.read_text())
        if m['inputs']==current and all((folder/f).exists() and sha(folder/f)==h for f,h in m['outputs'].items()):
            return pd.read_csv(folder/'summary.csv')
    records=[]
    with context(folder):
        for site in sites.itertuples(index=False):
            for mode in MODES[:2]:
                rec,_,_=pilot.solve(site,mode);rec['site_id']=site.site_id;records.append(rec)
    pd.DataFrame(records).to_csv(folder/'summary.csv',index=False,lineterminator='\n')
    files=[folder/'summary.csv']+list(folder.glob('*hourly.csv.gz'))
    marker.write_text(json.dumps(dict(inputs=current,outputs={p.name:sha(p) for p in files}),indent=2)+'\n')
    return pd.DataFrame(records)

def build(scenario,offgrid):
    sites,routes,params=setup();sc=CONFIG['scenarios'][scenario]
    profiles={}
    with context():
        for s in sites.itertuples(index=False):
            _,cf,load=pilot.weather_and_load(s);profiles[s.site_id]=(cf,load)
    snapshots=next(iter(profiles.values()))[0].index
    available=pd.Series((~((snapshots.hour+2)%24).isin(sc['outage_local_hours'])).astype(float),index=snapshots)
    background=next(iter(profiles.values()))[1].copy();background*=CONFIG['background_peak_MW']/background.max()
    n=pypsa.Network();n.set_snapshots(snapshots)
    n.add('Carrier',['electricity','battery','solar','diesel','bulk','portfolio'])
    n.add('Bus','regional',carrier='electricity')
    n.add('Load','existing_background',bus='regional',p_set=background)
    bulk_mc=params['bulk_grid_supply']*1000
    diesel_mc=(params['diesel_delivered_price']*params['diesel_specific_fuel']+params['diesel_variable_om'])*1000
    n.add('Generator','existing_supply',bus='regional',carrier='bulk',p_nom=sc['existing_supply_MW'],p_max_pu=available,marginal_cost=bulk_mc)
    n.add('Generator','restored_supply',bus='regional',carrier='bulk',p_nom=CONFIG['upstream_repaired_capacity_MW'],p_max_pu=available,marginal_cost=bulk_mc)
    # Dedicated background backup cannot subsidise settlement supply through the regional bus.
    n.add('Generator','background_backup',bus='regional',carrier='diesel',p_nom=CONFIG['background_peak_MW'],marginal_cost=diesel_mc)
    packages={};choices=offgrid.set_index(['site_id','mode'])
    for s in sites.itertuples(index=False):
        sid=s.site_id;cf,load=profiles[sid]
        n.add('Bus',sid,carrier='electricity',x=s.lon,y=s.lat)
        n.add('Bus',sid+'_service',carrier='electricity',x=s.lon,y=s.lat)
        n.add('Bus',sid+'_battery',carrier='battery')
        n.add('Load',sid+'_load',bus=sid+'_service',p_set=load)
        for mode in MODES[:2]:
            n.add('Generator',sid+'_'+mode,bus=sid+'_service',carrier='portfolio',p_nom=float(load.max()))
        n.add('Link',sid+'_delivery',bus0=sid,bus1=sid+'_service',efficiency=1-BASE['grid_distribution_loss'],p_nom=float(load.max())/(1-BASE['grid_distribution_loss']))
        with context():
            _,q,ledger,_,unit,groups=pilot.cost_context(s,'grid_extension')
        q['mv_line']=0
        q['transformer_100kVA']=max(1,np.ceil(load.max()*1000/(.08*1000*(1-BASE['grid_distribution_loss']))))
        q['fuel_tank_ats']=1 if sid=='S1' else 0
        fixed=ledger(q);packages[sid]=dict(q=q,unit=unit,groups=groups,intercept=fixed_eac(fixed),initial=fixed['summary']['initial_budget_USD'],ledger=ledger)
        # Declared candidate architecture: one shared grid backup hub at S1.
        # Off-grid alternatives retain a separate system at each settlement.
        count=float(sites.num_connections.sum()) if sid=='S1' else 0.
        n.add('Generator',sid+'_pv',bus=sid,carrier='solar',p_nom_extendable=True,p_nom_max=count*BASE['pv_capacity_limit_kWp_per_service_point']/1000,p_max_pu=cf,capital_cost=unit['pv']*1000)
        n.add('Generator',sid+'_diesel',bus=sid,carrier='diesel',p_nom_extendable=True,p_nom_max=count*BASE['diesel_limit_kW_per_service_point']/1000,capital_cost=unit['diesel']*1000,marginal_cost=diesel_mc)
        n.add('Store',sid+'_storage',bus=sid+'_battery',carrier='battery',e_nom_extendable=True,e_nom_max=count*BASE['battery_limit_kWh_per_service_point']/1000,e_min_pu=BASE['battery_min_soc'],e_max_pu=BASE['battery_max_soc'],e_cyclic=True,capital_cost=unit['battery']*1000)
        n.add('Link',sid+'_charge',bus0=sid,bus1=sid+'_battery',efficiency=BASE['battery_charge_efficiency'],p_nom_extendable=True,p_nom_max=count*BASE['converter_limit_kW_per_service_point']/1000,capital_cost=unit['converter']*1000,marginal_cost=.001)
        n.add('Link',sid+'_discharge',bus0=sid+'_battery',bus1=sid,efficiency=BASE['battery_discharge_efficiency'],p_nom_extendable=True,p_nom_max=count*BASE['converter_limit_kW_per_service_point']/1000/BASE['battery_discharge_efficiency'])
    n.add('Link','common_feeder',bus0='regional',bus1='S1',p_nom=CONFIG['common_feeder_capacity_MW'],efficiency=CONFIG['common_feeder_efficiency'])
    for edge in routes.itertuples(index=False):
        for suffix,a,b in [('f',edge.from_site,edge.to_site),('r',edge.to_site,edge.from_site)]:
            n.add('Link',edge.edge_id+'_'+suffix,bus0=a,bus1=b,p_nom=edge.capacity_MW,efficiency=edge.efficiency)
    route_costs={r.edge_id:infrastructure_cost('mv_line',r.route_km) for r in routes.itertuples(index=False)}
    repair_costs=dict(feeder=infrastructure_cost('mv_line',repair_km=CONFIG['common_feeder_repair_km']),upstream=infrastructure_cost('upstream_repair'))
    # New dedicated backup for the existing-load block is costed once in every case.
    background_capital=infrastructure_cost('diesel_genset',CONFIG['background_peak_MW']*1000)
    tank=infrastructure_cost('fuel_tank_ats');background_capital={k:background_capital[k]+tank[k] for k in tank}

    def extra(network,sns):
        m=network.model
        labels=pd.Index([sid+'_'+mode for sid in sites.site_id for mode in MODES],name='choice')
        z=m.add_variables(binary=True,coords=[labels],name='service_choice')
        y=m.add_variables(binary=True,coords=[pd.Index(routes.edge_id,name='edge')],name='route_build')
        r=m.add_variables(binary=True,coords=[pd.Index(['feeder','upstream'],name='repair')],name='repair_asset')
        flows=m.variables['Link-p'];generators=m.variables['Generator-p'];gp=m.variables['Generator-p_nom'];lp=m.variables['Link-p_nom'];sp=m.variables['Store-e_nom']
        for s in sites.itertuples(index=False):
            sid=s.site_id;load=profiles[sid][1].rename_axis('snapshot').to_xarray();zg=z.sel(choice=sid+'_grid')
            m.add_constraints(sum(z.sel(choice=sid+'_'+mode) for mode in MODES)==1,name=sid+'_one_service')
            # Off-grid options have identical delivered profiles and no coupling.
            # The more expensive one is dominated at every joint solution.
            worse=max(MODES[:2],key=lambda mode:float(choices.loc[(sid,mode),'equivalent_annual_cost_USD']))
            m.add_constraints(z.sel(choice=sid+'_'+worse)==0,name=sid+'_dominated_offgrid')
            m.add_constraints(zg<=r.sel(repair='feeder'),name=sid+'_feeder_required')
            for mode in MODES[:2]:
                m.add_constraints(generators.sel(name=sid+'_'+mode)==load*z.sel(choice=sid+'_'+mode),name=sid+'_'+mode+'_fixed_service')
            m.add_constraints(flows.sel(name=sid+'_delivery')*(1-BASE['grid_distribution_loss'])==load*zg,name=sid+'_grid_service')
            for asset in ['pv','diesel']:
                name=sid+'_'+asset;m.add_constraints(gp.sel(name=name)<=n.generators.at[name,'p_nom_max']*zg,name=name+'_activate')
            name=sid+'_storage';m.add_constraints(sp.sel(name=name)<=n.stores.at[name,'e_nom_max']*zg,name=name+'_activate')
            m.add_constraints(lp.sel(name=sid+'_charge')<=n.links.at[sid+'_charge','p_nom_max']*zg,name=sid+'_converter_activate')
            m.add_constraints(lp.sel(name=sid+'_charge')==BASE['battery_discharge_efficiency']*lp.sel(name=sid+'_discharge'),name=sid+'_converter_rating')
            m.add_constraints(flows.sel(name=sid+'_charge')+BASE['battery_discharge_efficiency']*flows.sel(name=sid+'_discharge')<=lp.sel(name=sid+'_charge'),name=sid+'_converter_throughput')
        # Shared grid PV/backup can flow between connected sites; use one aggregate grid diesel cap.
        m.add_constraints(sum(generators.sel(name=sid+'_diesel').sum() for sid in sites.site_id)<=sum(profiles[sid][1].sum()*BASE['diesel_max_fraction_of_delivered_energy']*z.sel(choice=sid+'_grid') for sid in sites.site_id),name='grid_diesel_energy_budget')
        m.add_constraints(generators.sel(name='restored_supply')<=CONFIG['upstream_repaired_capacity_MW']*available.rename_axis('snapshot').to_xarray()*r.sel(repair='upstream'),name='restore_upstream')
        m.add_constraints(flows.sel(name='common_feeder')<=CONFIG['common_feeder_capacity_MW']*r.sel(repair='feeder'),name='restore_feeder')
        # Backup is limited to background demand; imports into the feeder cannot exceed bulk supply.
        m.add_constraints(generators.sel(name='background_backup')<=background.rename_axis('snapshot').to_xarray(),name='background_backup_only')
        m.add_constraints(flows.sel(name='common_feeder')<=generators.sel(name='existing_supply')+generators.sel(name='restored_supply'),name='no_diesel_grid_supply')
        m.add_constraints(sum(repair_costs[k]['initial']*r.sel(repair=k) for k in repair_costs)<=sc['repair_budget_USD'],name='repair_budget')
        # Single-commodity connectivity prevents a grid-labelled island with no physical route to the source.
        commodity=m.add_variables(lower=0,coords=[pd.Index([e+'_'+direction for e in routes.edge_id for direction in ['f','r']],name='arc')],name='connectivity_flow')
        for edge in routes.itertuples(index=False):
            m.add_constraints(y.sel(edge=edge.edge_id)<=r.sel(repair='feeder'),name=edge.edge_id+'_feeder_required')
            m.add_constraints(flows.sel(name=edge.edge_id+'_f')+flows.sel(name=edge.edge_id+'_r')<=edge.capacity_MW*y.sel(edge=edge.edge_id),name=edge.edge_id+'_capacity')
            for direction in ['f','r']:
                m.add_constraints(commodity.sel(arc=edge.edge_id+'_'+direction)<=len(sites)*y.sel(edge=edge.edge_id),name=edge.edge_id+'_'+direction+'_connectivity_capacity')
        total_grid=sum(z.sel(choice=sid+'_grid') for sid in sites.site_id)
        m.add_constraints(total_grid<=len(sites)*r.sel(repair='feeder'),name='grid_requires_feeder')
        m.add_constraints(r.sel(repair='feeder')<=z.sel(choice='S1_grid'),name='shared_hub_requires_anchor_service')
        # Valid rooted cutset inequalities strengthen the commodity formulation.
        # With four nodes there are only seven nonempty root-excluding subsets.
        nonroot=[sid for sid in sites.site_id if sid!='S1']
        for size in range(1,len(nonroot)+1):
            for subset_tuple in itertools.combinations(nonroot,size):
                subset=set(subset_tuple)
                crossing=[edge.edge_id for edge in routes.itertuples() if (edge.from_site in subset)!=(edge.to_site in subset)]
                for sid in subset:
                    m.add_constraints(sum(y.sel(edge=e) for e in crossing)>=z.sel(choice=sid+'_grid'),name='cut_'+'_'.join(subset_tuple)+'_'+sid)
        for sid in sites.site_id:
            balance=total_grid if sid=='S1' else 0
            for edge in routes.itertuples(index=False):
                if edge.from_site==sid:balance=balance+commodity.sel(arc=edge.edge_id+'_r')-commodity.sel(arc=edge.edge_id+'_f')
                if edge.to_site==sid:balance=balance+commodity.sel(arc=edge.edge_id+'_f')-commodity.sel(arc=edge.edge_id+'_r')
            m.add_constraints(balance==z.sel(choice=sid+'_grid'),name=sid+'_connected')
        fixed=sum(float(choices.loc[(sid,mode),'equivalent_annual_cost_USD'])*z.sel(choice=sid+'_'+mode) for sid in sites.site_id for mode in MODES[:2])
        fixed+=sum(packages[sid]['intercept']*z.sel(choice=sid+'_grid') for sid in sites.site_id)
        fixed+=sum(route_costs[e]['eac']*y.sel(edge=e) for e in routes.edge_id)
        fixed+=sum(repair_costs[k]['eac']*r.sel(repair=k) for k in repair_costs)
        m.objective+=fixed
    return n,extra,dict(sites=sites,routes=routes,params=params,profiles=profiles,packages=packages,route_costs=route_costs,repair_costs=repair_costs,background_capital=background_capital,background=background,availability=available)

def solve(scenario,offgrid):
    folder=OUT/scenario;folder.mkdir(parents=True,exist_ok=True)
    (folder/'solver.log').write_text('')
    n,extra,ctx=build(scenario,offgrid)
    status,termination=n.optimize(solver_name='highs',extra_functionality=extra,include_objective_constant=False,
        solver_options={'threads':4,'mip_lp_solver':'ipm','mip_rel_gap':CONFIG['mip_relative_gap'],'log_to_console':False,'log_file':str(folder/'solver.log'),'time_limit':1200})
    if status!='ok' or termination!='optimal':raise RuntimeError(f'{scenario}: {status}/{termination}; no successful result published')
    info=n.model.solver_model.getInfo()
    print(f'{scenario}: objective {n.objective:.2f}; MIP gap {info.mip_gap}',flush=True)
    decisions={k:n.model.variables[k].solution.to_series() for k in ['service_choice','route_build','repair_asset','connectivity_flow']}
    for k,v in decisions.items():v.rename('value').to_csv(folder/(k+'.csv'),lineterminator='\n')
    n.export_to_netcdf(folder/'network.nc')
    records=[];choices=offgrid.set_index(['site_id','mode'])
    for s in ctx['sites'].itertuples(index=False):
        sid=s.site_id;mode=max(MODES,key=lambda mode:decisions['service_choice'][sid+'_'+mode]);cf,load=ctx['profiles'][sid]
        if mode!='grid':
            o=choices.loc[(sid,mode)];caps={k:float(o[k]) for k in ['pv_kWp','battery_nominal_kWh','converter_AC_kW','diesel_kW']}
            local_eac=float(o.equivalent_annual_cost_USD);initial=float(o.initial_budget_USD)
        else:
            caps=dict(pv_kWp=n.generators.at[sid+'_pv','p_nom_opt']*1000,diesel_kW=n.generators.at[sid+'_diesel','p_nom_opt']*1000,battery_nominal_kWh=n.stores.at[sid+'_storage','e_nom_opt']*1000,converter_AC_kW=n.links.at[sid+'_charge','p_nom_opt']*1000)
            package=ctx['packages'][sid];q=dict(package['q'])
            for asset,key in [('pv','pv_kWp'),('diesel','diesel_kW'),('battery','battery_nominal_kWh'),('converter','converter_AC_kW')]:
                for component in package['groups'][asset]:q[component]=max(0,caps[key])
            ledger=package['ledger'](q);initial=ledger['summary']['initial_budget_USD'];local_eac=fixed_eac(ledger)
            local_eac+=n.generators_t.p[sid+'_diesel'].sum()*n.generators.at[sid+'_diesel','marginal_cost']
        records.append(dict(scenario=scenario,site_id=sid,geohash=s.geohash,source_name=s.village_name,connections=s.num_connections,choice=mode,annual_delivered_kWh=load.sum()*1000,local_equipment_and_operation_EAC_USD=local_eac,local_initial_USD=initial,**caps))
    decisions_table=pd.DataFrame(records);decisions_table.to_csv(folder/'settlements.csv',index=False,lineterminator='\n')
    annual_shared=sum(ctx['route_costs'][e]['eac']*decisions['route_build'][e] for e in ctx['routes'].edge_id)+sum(ctx['repair_costs'][k]['eac']*decisions['repair_asset'][k] for k in ctx['repair_costs'])
    shared_initial=sum(ctx['route_costs'][e]['initial']*decisions['route_build'][e] for e in ctx['routes'].edge_id)+sum(ctx['repair_costs'][k]['initial']*decisions['repair_asset'][k] for k in ctx['repair_costs'])
    regional_cost=sum(n.generators_t.p[k].sum()*n.generators.at[k,'marginal_cost'] for k in ['existing_supply','restored_supply','background_backup'])
    penalty=n.links_t.p0.filter(like='_charge').sum().sum()*.001
    eac=decisions_table.local_equipment_and_operation_EAC_USD.sum()+annual_shared+regional_cost+ctx['background_capital']['eac']
    result=dict(scenario=scenario,solver_status=status,termination=termination,mip_relative_gap=float(info.mip_gap),mip_dual_bound_USD=float(info.mip_dual_bound),
        objective_excluding_background_fixed_USD=float(n.objective),numerical_charge_penalty_USD=float(penalty),
        equivalent_annual_cost_USD=float(eac),lifecycle_NPC_USD=float(eac/annuity(ctx['params']['real_discount_rate'],ctx['params']['horizon_years'])),
        initial_investment_USD=float(decisions_table.local_initial_USD.sum()+shared_initial+ctx['background_capital']['initial']),
        repair_spend_USD=float(sum(ctx['repair_costs'][k]['initial']*decisions['repair_asset'][k] for k in ctx['repair_costs'])),
        background_fixed_EAC_USD=ctx['background_capital']['eac'],regional_variable_USD=float(regional_cost),shared_asset_EAC_USD=float(annual_shared),
        existing_background_MWh=float(ctx['background'].sum()),settlement_service_MWh=float(decisions_table.annual_delivered_kWh.sum()/1000),
        new_feeder_km=float(sum(r.route_km*decisions['route_build'][r.edge_id] for r in ctx['routes'].itertuples())),
        repaired_common_feeder_km=float(CONFIG['common_feeder_repair_km']*decisions['repair_asset']['feeder']),
        restored_upstream_MW=float(CONFIG['upstream_repaired_capacity_MW']*decisions['repair_asset']['upstream']),
        grid_connections=int(decisions_table.loc[decisions_table.choice=='grid','connections'].sum()),
        mini_grid_connections=int(decisions_table.loc[decisions_table.choice=='mini_grid','connections'].sum()),
        standalone_connections=int(decisions_table.loc[decisions_table.choice=='standalone','connections'].sum()))
    result['objective_reconstruction_error_USD']=float(eac-(n.objective-penalty+ctx['background_capital']['eac']))
    if abs(result['objective_reconstruction_error_USD'])>.1:raise AssertionError(result)
    (folder/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
    return result

def run(force=False):
    OUT.mkdir(parents=True,exist_ok=True);manifest=OUT/'manifest.json';current=fingerprints()
    if not force and manifest.exists():
        m=json.loads(manifest.read_text())
        if m['complete'] and m['inputs']==current and all((OUT/p).exists() and sha(OUT/p)==h for p,h in m['outputs'].items()):return pd.read_csv(OUT/'summary.csv')
    sites,_,_=setup();offgrid=prepare_offgrid(sites);records=[]
    for scenario in CONFIG['scenario_order']:
        print('Solving joint recovery scenario: '+scenario,flush=True);records.append(solve(scenario,offgrid))
    summary=pd.DataFrame(records);summary.to_csv(OUT/'summary.csv',index=False,lineterminator='\n')
    files=[OUT/'summary.csv']+list((OUT/'offgrid').glob('*'))
    for scenario in CONFIG['scenario_order']:files+=list((OUT/scenario).glob('*'))
    manifest.write_text(json.dumps(dict(complete=True,inputs=current,outputs={p.relative_to(OUT).as_posix():sha(p) for p in files},
        pypsa_version=pypsa.__version__,interpretation='Joint optimum within declared four-cluster candidate graph and provisional recovery scenarios; no national or field validation'),indent=2)+'\n')
    return summary

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--force',action='store_true');args=parser.parse_args();run(args.force)
