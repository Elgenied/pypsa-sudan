"""Six-state, full-year candidate-portfolio selection and national corridor recovery.

Local portfolios are sized per zone with that zone's own weather point and fixed before the MIP. The bound certifies this finite library,
not unrestricted local equipment, routing, electricity-access status or war damage.
"""
from pathlib import Path
import argparse,json
import numpy as np
import pandas as pd
import pypsa
import regional_library as lib
import coupled_model as coupled
from cost_model import annuity

ROOT=lib.ROOT;DATA=lib.DATA;OUT=Path(__file__).resolve().parent/'results/regional'
CONFIG=lib.CONFIG
HYDRO={'Merowe':'M-HP','Khartoum':'Jeb-HP','Roseires':'Ros-HP','Sennar':'Sen-HP','Gedaref':'UpA-HP','Kassala':'KhE-HP'}

def fingerprints():
    out=lib.fingerprints()
    for p in [Path(__file__),ROOT/'research/system_costs/coupled_model.py',ROOT/'data/national_coupling/national_reference.nc',ROOT/'data/national_coupling/national_2022.csv',ROOT/'research/forecasting_2012/data/hydro_monthly.csv']:
        out[p.relative_to(ROOT).as_posix()]=lib.r.sha(p)
    return out

def valid(folder):
    path=folder/'manifest.json'
    if not path.exists():return False
    m=json.loads(path.read_text());return m['inputs']==fingerprints() and all((folder/x).exists() and lib.r.sha(folder/x)==h for x,h in m['outputs'].items())

def stamp(folder,files):
    (folder/'manifest.json').write_text(json.dumps(dict(inputs=fingerprints(),outputs={x.relative_to(folder).as_posix():lib.r.sha(x) for x in files}),indent=2)+'\n')

def monthly_budgets(n):
    history=pd.read_csv(ROOT/'research/forecasting_2012/data/hydro_monthly.csv')
    rows=[]
    for name,g in n.generators.query("carrier == 'hydro'").iterrows():
        shape=history[history.plant_id.eq(HYDRO[g.bus])].set_index('month').mean_generation_mwh_per_day
        energy=np.array([shape[m]*pd.Timestamp(2022,m,1).days_in_month for m in range(1,13)])
        for m,v in enumerate(energy/energy.sum()*g.e_sum_max,1):rows.append(dict(generator=name,month=m,budget_MWh=v))
    return pd.DataFrame(rows)

def options(zones,scenario,library,demand_factor=1,fuel_factor=1):
    return pd.DataFrame([lib.package(z,mode,scenario,library,demand_factor,fuel_factor) for z in zones.itertuples() for mode in ['grid','mini_grid','standalone']])

def build(scenario,policy,zones,opts,library,fuel_factor=1):
    n=coupled.national_network(np.zeros(8760));n.remove('Load','additional_access')
    n.add('Carrier','portfolio_accounting')
    # Remove allocated residential demand AND its proportional historical accounting
    # losses; reintroduce the complete chosen service through explicit local losses.
    for bus in zones.supply_bus.unique():
        for suffix in [' consumption',' losses']:n.loads_t.p_set[bus+suffix]*=1-CONFIG['residential_share']
    thermal=n.generators.carrier.eq('combustible');n.generators.loc[thermal,'marginal_cost']*=fuel_factor
    repair=pd.read_csv(DATA/'corridor_register.csv').set_index('asset_id')
    for name,e in repair.iterrows():n.links.at[name,'p_nom']=e.reference_MW # gates below apply to signed transfers
    fixed=opts[opts['mode'].ne('grid')].sort_values(['local_EAC_USD','mode']).drop_duplicates('zone_id').set_index('zone_id')
    grid=opts[opts['mode'].eq('grid')].set_index('zone_id')
    # Each zone has its own weather point, hence its own grid-import shape: one accounting generator per zone.
    interface={};service={}
    for z in zones.itertuples():
        row=library.set_index('key').loc[grid.at[z.zone_id,'key']]
        hourly=pd.read_csv(lib.OUT/row.hourly_file,index_col=0,parse_dates=True)
        series=pd.Series(hourly.grid_MW.to_numpy(),index=n.snapshots);maximum=float(series.max());scale=float(grid.at[z.zone_id,'scale'])
        assert maximum>0,z.zone_id
        service[z.supply_bus]=service.get(z.supply_bus,0.)+series*scale
        n.add('Generator','cancel_'+z.zone_id,bus=z.supply_bus,carrier='portfolio_accounting',p_nom_extendable=True,p_nom_max=maximum*scale,
              p_max_pu=series/maximum,p_min_pu=series/maximum)
        interface[z.zone_id]=dict(bus=z.supply_bus,peak=maximum,scale=scale)
    for bus,series in service.items():n.add('Load','service_'+bus,bus=bus,p_set=series)
    budgets=monthly_budgets(n);projects=repair[repair.candidate_repair].copy()
    params={k:float(v['central']) for k,v in lib.inputs()[1].items()}
    annual_factor=annuity(params['real_discount_rate'],CONFIG['repair_life_years'])+CONFIG['repair_annual_om_fraction']
    def extra(network,sns):
        m=network.model;one=m.add_variables(lower=1,upper=1,name='accounting_one')
        z=m.add_variables(binary=True,coords=[pd.Index(zones.zone_id,name='zone')],name='grid_choice')
        r=m.add_variables(binary=True,coords=[pd.Index(projects.index,name='project')],name='corridor_repair')
        if policy!='mixed':m.add_constraints(z==(1 if policy=='grid_led' else 0),name='policy_choices')
        if CONFIG['scenarios'][scenario]['force_repairs']:m.add_constraints(r==1,name='restored_backbone')
        cost=sum(projects.at[e,'repair_initial_USD']*r.sel(project=e) for e in projects.index)
        m.add_constraints(cost<=CONFIG['scenarios'][scenario]['repair_budget_USD'],name='repair_budget')
        for name,e in projects.iterrows():
            limit=e.reference_MW*(e.available_fraction+(1-e.available_fraction)*r.sel(project=name))
            m.add_constraints(m.variables['Link-p'].sel(name=name)<=limit,name=name+'_upper_recovery')
            m.add_constraints(m.variables['Link-p'].sel(name=name)>=-limit,name=name+'_lower_recovery')
        for zid,values in interface.items():
            m.add_constraints(m.variables['Generator-p_nom'].sel(name='cancel_'+zid)==values['scale']*values['peak']*(one-z.sel(zone=zid)),name=zid+'_service_accounting')
        for b in budgets.itertuples():
            snapshots=sns[sns.month==b.month]
            m.add_constraints(m.variables['Generator-p'].sel(name=b.generator,snapshot=snapshots).sum()<=b.budget_MWh,name=b.generator.replace(' ','_')+f'_month_{b.month}')
        local=sum(grid.at[zid,'local_EAC_USD']*z.sel(zone=zid)+fixed.at[zid,'local_EAC_USD']*(one-z.sel(zone=zid)) for zid in zones.zone_id)
        m.objective+=local+cost*annual_factor
    return n,extra,fixed,grid,projects,budgets,annual_factor

def case(scenario,policy='mixed',zone_count=36,demand_factor=1.,fuel_factor=1.):
    key=f'{scenario}_{policy}_{zone_count}_d{demand_factor:g}_f{fuel_factor:g}';folder=OUT/key
    if valid(folder):return json.loads((folder/'summary.json').read_text())
    folder.mkdir(parents=True,exist_ok=True)
    library=lib.run();zones=lib.zones(zone_count)
    opts=options(zones,scenario,library,demand_factor,fuel_factor)
    n,extra,off,grid,projects,budgets,annual_factor=build(scenario,policy,zones,opts,library,fuel_factor)
    print('Solving regional case',key,flush=True)
    (folder/'solver.log').write_text('')
    status,term=n.optimize(solver_name='highs',extra_functionality=extra,
        solver_options={'threads':4,'mip_lp_solver':'ipm','mip_rel_gap':CONFIG['mip_gap'],'time_limit':CONFIG['time_limit_seconds'],
                        'log_to_console':False,'log_file':str(folder/'solver.log')})
    diagnostic=False
    if term=='infeasible' and policy!='mixed':
        # Diagnose a failed benchmark; these are explicitly unmet demand, never supply.
        diagnostic=True
        print(key,'infeasible; solving labelled supply-shortfall diagnostic',flush=True)
        n.add('Carrier','unserved_diagnostic')
        for bus in n.buses.index:
            n.add('Generator','unserved_'+bus,bus=bus,carrier='unserved_diagnostic',p_nom=100000,marginal_cost=1e6)
        status,term=n.optimize(solver_name='highs',extra_functionality=extra,
            solver_options={'threads':4,'mip_lp_solver':'ipm','mip_rel_gap':CONFIG['mip_gap'],'time_limit':CONFIG['time_limit_seconds'],
                            'log_to_console':False,'log_file':str(folder/'diagnostic_solver.log')})
    if (status,term)!=('ok','optimal'):raise RuntimeError(f'{key}: {status}/{term}; no completed result')
    z=n.model.variables['grid_choice'].solution.to_series();r=n.model.variables['corridor_repair'].solution.to_series()
    selected=pd.DataFrame([grid.loc[zid] if z[zid]>.5 else off.loc[zid] for zid in zones.zone_id]);selected.index.name='zone_id';selected=selected.reset_index()
    deficit_cols=n.generators.index[n.generators.carrier.eq('unserved_diagnostic')]
    shortfall=float(n.generators_t.p[deficit_cols].sum().sum())
    national_cost=float((n.generators_t.p.sum()*n.generators.marginal_cost).sum())-shortfall*1e6
    repairs=projects.copy();repairs['selected']=r;repairs['spend_USD']=repairs.repair_initial_USD*r
    initial=float(selected.initial_USD.sum()+repairs.spend_USD.sum());repair_eac=float(repairs.spend_USD.sum()*annual_factor)
    objective=float(selected.local_EAC_USD.sum()+national_cost+repair_eac)
    assert abs(objective+shortfall*1e6-n.objective)<max(1.,abs(n.objective)*1e-9),(objective,n.objective)
    info=n.model.solver_model.getInfo()
    summary=dict(case=key,scenario=scenario,policy=policy,zones=zone_count,demand_factor=demand_factor,thermal_cost_factor=fuel_factor,
        status='infeasible_benchmark_diagnostic' if diagnostic else 'optimal_candidate_portfolio',unserved_MWh=shortfall,
        shortfall_hours=int((n.generators_t.p[deficit_cols].sum(axis=1)>1e-6).sum()),
        annual_system_cost_USD=None if diagnostic else objective,diagnostic_resource_cost_USD=objective if diagnostic else None,
        local_annual_cost_USD=float(selected.local_EAC_USD.sum()),national_operating_cost_USD=national_cost,
        annual_repair_cost_USD=repair_eac,repair_investment_USD=float(repairs.spend_USD.sum()),initial_local_and_repair_USD=initial,
        target_residential_MWh=float(selected.target_MWh.sum()),baseline_allocated_residential_MWh=float(zones.baseline_residential_MWh.sum()),
        uplift_MWh=float(selected.target_MWh.sum()-zones.baseline_residential_MWh.sum()),grid_import_MWh=float(selected.grid_import_MWh.sum()),
        local_diesel_MWh=float(selected.diesel_MWh.sum()),mip_gap=float(info.mip_gap),lower_bound_USD=float(info.mip_dual_bound),
        objective_USD=float(n.objective),hours=8760,source_clusters=int(selected.clusters.sum()),potential_connections=int(selected.connections.sum()),
        **{m+'_connections':int(selected.loc[selected['mode'].eq(m),'connections'].sum()) for m in ['grid','mini_grid','standalone']},
        weather='one NASA POWER point per zone',scope='Finite-portfolio, whole-zone choice under schematic network and recovery assumptions; not unrestricted design optimality')
    opts.to_csv(folder/'options.csv',index=False,lineterminator='\n');selected.to_csv(folder/'zone_choices.csv',index=False,lineterminator='\n')
    repairs.to_csv(folder/'repairs.csv',lineterminator='\n');budgets.to_csv(folder/'hydro_budgets.csv',index=False,lineterminator='\n')
    n.generators_t.p.sum().groupby(n.generators.carrier).sum().rename('MWh').to_csv(folder/'generation.csv',lineterminator='\n')
    n.export_to_netcdf(folder/'network.nc')
    (folder/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    stamp(folder,[folder/x for x in ['options.csv','zone_choices.csv','repairs.csv','hydro_budgets.csv','generation.csv','network.nc','summary.json','solver.log']]+([folder/'diagnostic_solver.log'] if diagnostic else []))
    print(key,'completed',objective,'gap',info.mip_gap,flush=True);return summary

def run():
    OUT.mkdir(parents=True,exist_ok=True)
    if valid(OUT):return pd.read_csv(OUT/'summary.csv')
    rows=[case(s,p) for s in CONFIG['scenarios'] for p in ['mixed','grid_led','decentralized']]
    rows.extend([case('selective','mixed',48),case('selective','mixed',36,1.2),case('selective','mixed',36,1.,1.25)])
    table=pd.DataFrame(rows);table.to_csv(OUT/'summary.csv',index=False,lineterminator='\n')
    files=[OUT/'summary.csv']+[x for d in OUT.iterdir() if d.is_dir() and d.name!='library' for x in d.iterdir() if x.is_file() and x.name!='manifest.json']
    stamp(OUT,files);return table

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--case',choices=list(CONFIG['scenarios']));parser.add_argument('--policy',default='mixed',choices=['mixed','grid_led','decentralized']);args=parser.parse_args()
    case(args.case,args.policy) if args.case else run()
