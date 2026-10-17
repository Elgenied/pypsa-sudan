"""Hourly PyPSA sizing for three real DRE clusters under explicit planning assumptions.

Reuses the complete system cost ledger: the LP minimizes its exact linear annualized
cost, including replacement costs, rather than optimizing equipment-only CAPEX.
"""
from pathlib import Path
import argparse, copy, hashlib, json, logging
import numpy as np
import pandas as pd
import pypsa
from cost_model import load_inputs, evaluate, annuity

ROOT=Path(__file__).resolve().parents[2]
DATA=ROOT/'data/electrification_pilot'
OUT=Path(__file__).resolve().parent/'results/pilot'
MODES=('standalone','mini_grid','grid_extension')
CONFIG=json.loads((DATA/'config.json').read_text())
for name in ('pypsa','linopy'):
    logging.getLogger(name).setLevel(logging.WARNING)


def fingerprint():
    files=list(DATA.glob('*.json'))+list(DATA.glob('*.csv'))+list(DATA.glob('*.gz'))
    files+=list((ROOT/'data/system_costs').glob('*.csv'))
    files += [Path(__file__),Path(__file__).with_name('cost_model.py')]
    return {p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes().replace(b'\r\n',b'\n') if p.suffix!='.gz' else p.read_bytes()).hexdigest()
            for p in sorted(files)}


def weather_and_load(site, demand_multiplier=1):
    w=pd.read_csv(DATA/f'weather_{site.geohash}_2022.csv.gz',parse_dates=['time_UTC']).set_index('time_UTC')
    assert len(w)==8760 and w.index.is_unique and w.index.equals(pd.date_range('2022-01-01',periods=8760,freq='h'))
    ghi=w.ALLSKY_SFC_SW_DWN.clip(lower=0)
    # Horizontal-array screening approximation, NOT a calibrated tilted-plane/PVWatts model.
    cell_temp=w.T2M+(CONFIG['pv_NOCT_C']-20)*ghi/800
    cf=(ghi/1000*CONFIG['pv_misc_dc_efficiency']*CONFIG['pv_inverter_efficiency']
        *(1+CONFIG['pv_temperature_coefficient']*(cell_temp-25))).clip(0,1)
    local_hour=(w.index.hour+CONFIG['local_UTC_offset_hours'])%24
    weights=np.array(CONFIG['hourly_demand_weights'],float)
    load=pd.Series(weights[local_hour]/weights.sum()*CONFIG['daily_kWh_per_service_point']
                   *float(site.num_connections)*demand_multiplier/1000,index=w.index)
    assert np.isclose(load.sum()*1000,site.num_connections*365*demand_multiplier*CONFIG['daily_kWh_per_service_point'])
    return w,cf,load


def cost_context(site, mode, multiplier=1):
    inputs=copy.deepcopy(load_inputs())
    if mode=='standalone':
        # Explicit small-system purchasing premium; does not claim a Sudan price survey.
        for component in inputs[0].values():
            if component['imported']:
                for field in ('low_USD','base_USD','high_USD'):
                    component[field]*=CONFIG['standalone_hardware_markup']
    q={k:0. for k in inputs[0]}
    q['house_wiring']=float(site.num_connections)
    if mode!='standalone':
        q.update(lv_line=CONFIG['lv_length_factor']*np.sqrt(site.num_connections*site.hull_area),
                 service_meter=float(site.num_connections),civil_site=1,land_right=1)
    if mode=='mini_grid':
        q['fuel_tank_ats']=1  # Fixed backup-ready architecture; no binary tank-investment choice.
    if mode=='grid_extension':
        q.update(mv_line=CONFIG['mv_route_factor']*site.distance_to_existing_transmission_lines,
                 transformer_100kVA=1,grid_protection=1)
    design=dict(connections=float(site.num_connections),daily_kWh_per_connection=CONFIG['daily_kWh_per_service_point']*multiplier,
                diesel_generation_fraction=0,repair_mv_route_km=0,repair_cost_fraction=0)
    def ledger(quantities):
        return evaluate(mode,inputs=inputs,quantity_overrides=quantities,design_overrides=design)
    def fixed_cost(o):
        # Replace assumed annual grid/fuel usage with actual optimized hourly operation later.
        return o['summary']['equivalent_annual_cost_USD']-sum(o['operating'][k] for k in
                         ('grid_supply','diesel_fuel','diesel_runtime_maintenance'))
    base=ledger(q); intercept=fixed_cost(base)
    groups={'pv':['pv_module','pv_bos','pv_inverter'],'battery':['battery'],
            'converter':['battery_inverter'],'diesel':['diesel_genset']}
    costs={}
    for asset,parts in groups.items():
        augmented=dict(q)
        for component in parts:
            augmented[component]+=1
        costs[asset]=fixed_cost(ledger(augmented))-intercept
        assert costs[asset]>0
    return inputs,q,ledger,intercept,costs,groups


def solve(site, mode, scenario='base'):
    multiplier=2 if scenario=='double_demand' else 1
    weather,cf,delivered=weather_and_load(site,multiplier)
    inputs,q,cost_ledger,intercept,unit,groups=cost_context(site,mode,multiplier)
    params={k:float(v['central']) for k,v in inputs[1].items()}
    loss=0 if mode=='standalone' else CONFIG['mini_grid_distribution_loss' if mode=='mini_grid' else 'grid_distribution_loss']
    load=delivered/(1-loss)
    n=pypsa.Network();n.set_snapshots(load.index)
    n.add('Carrier',['electricity','battery','solar','diesel','grid'])
    n.add('Bus','ac',carrier='electricity');n.add('Bus','battery_bus',carrier='battery')
    n.add('Load','service',bus='ac',p_set=load)
    count=float(site.num_connections)
    n.add('Generator','pv',bus='ac',carrier='solar',p_nom_extendable=True,
          p_nom_max=count*CONFIG['pv_capacity_limit_kWp_per_service_point']/1000,
          p_max_pu=cf,capital_cost=unit['pv']*1000)
    eta_c=CONFIG['battery_charge_efficiency'];eta_d=CONFIG['battery_discharge_efficiency']
    n.add('Store','battery',bus='battery_bus',carrier='battery',e_nom_extendable=True,
          e_nom_max=count*CONFIG['battery_limit_kWh_per_service_point']/1000,
          e_min_pu=CONFIG['battery_min_soc'],e_max_pu=CONFIG['battery_max_soc'],
          e_cyclic=True,capital_cost=unit['battery']*1000)
    # Charge-side p_nom is AC input; discharge-side p_nom is DC input. Charge once per AC-rated converter.
    n.add('Link','charge',bus0='ac',bus1='battery_bus',carrier='battery',efficiency=eta_c,
          p_nom_extendable=True,p_nom_max=count*CONFIG['converter_limit_kW_per_service_point']/1000,
          capital_cost=unit['converter']*1000,marginal_cost=.001)
    n.add('Link','discharge',bus0='battery_bus',bus1='ac',carrier='battery',efficiency=eta_d,
          p_nom_extendable=True,p_nom_max=count*CONFIG['converter_limit_kW_per_service_point']/eta_d/1000)
    diesel_mc=(params['diesel_delivered_price']*params['diesel_specific_fuel']+params['diesel_variable_om'])*1000
    fuel_limit=delivered.sum()*CONFIG['diesel_max_fraction_of_delivered_energy']
    if mode=='mini_grid' and scenario!='no_diesel':
        n.add('Generator','diesel',bus='ac',carrier='diesel',p_nom_extendable=True,
              p_nom_max=count*CONFIG['diesel_limit_kW_per_service_point']/1000,
              capital_cost=unit['diesel']*1000,marginal_cost=diesel_mc,e_sum_max=fuel_limit)
    grid_availability=pd.Series(1.,index=n.snapshots)
    if scenario=='evening_outage':
        grid_availability.loc[((n.snapshots.hour+CONFIG['local_UTC_offset_hours'])%24).isin(CONFIG['outage_local_hours'])]=0
    if mode=='grid_extension':
        n.add('Generator','grid',bus='ac',carrier='grid',p_nom=CONFIG['grid_tie_capacity_kW']/1000,
              p_max_pu=grid_availability,marginal_cost=params['bulk_grid_supply']*1000)

    def constraints(network,snapshots):
        model=network.model
        capacity=model.variables['Link-p_nom']
        model.add_constraints(capacity.sel(name='charge')==eta_d*capacity.sel(name='discharge'),name='shared_converter_capacity')
        flows=model.variables['Link-p']
        model.add_constraints(flows.sel(name='charge')+eta_d*flows.sel(name='discharge')<=capacity.sel(name='charge'),name='shared_converter_throughput')
    status,condition=n.optimize(solver_name='highs',extra_functionality=constraints,
                                solver_options={'threads':2,'solver':'simplex','log_to_console':False},
                                include_objective_constant=False)
    if status!='ok' or condition!='optimal':
        raise RuntimeError(f'{site.geohash} {mode} {scenario}: {status}/{condition}')
    def gen(name):
        return n.generators_t.p[name] if name in n.generators.index else pd.Series(0.,index=n.snapshots)
    pv=gen('pv');diesel=gen('diesel');grid=gen('grid')
    charge=n.links_t.p0.charge;discharge=-n.links_t.p1.discharge;dc_discharge=n.links_t.p0.discharge
    energy=n.stores_t.e.battery
    caps=dict(pv=n.generators.at['pv','p_nom_opt']*1000,battery=n.stores.at['battery','e_nom_opt']*1000,
              converter=n.links.at['charge','p_nom_opt']*1000,
              diesel=n.generators.at['diesel','p_nom_opt']*1000 if 'diesel' in n.generators.index else 0)
    for asset,parts in groups.items():
        for component in parts:
            q[component]=max(0,float(caps[asset]))
    actual=cost_ledger(q)
    yearly=dict(grid_supply=grid.sum()*1000*params['bulk_grid_supply'],
                diesel_fuel=diesel.sum()*1000*params['diesel_specific_fuel']*params['diesel_delivered_price'],
                diesel_runtime_maintenance=diesel.sum()*1000*params['diesel_variable_om'])
    for row in actual['ledger']:
        if row['kind']=='operating' and row['item'] in yearly:
            row['cost_USD']=yearly[row['item']]
            row['discounted_cost_USD']=row['cost_USD']/(1+params['real_discount_rate'])**row['year']
    npc=sum(row['discounted_cost_USD'] for row in actual['ledger'])
    eac=npc*annuity(params['real_discount_rate'],params['horizon_years'])
    numerical_penalty=charge.sum()*.001
    objective_gap=intercept+n.objective-numerical_penalty-eac
    balance=pv+diesel+grid+discharge-charge-load
    prior=np.roll(energy.to_numpy(),1)
    storage_residual=energy.to_numpy()-prior-(eta_c*charge-dc_discharge).to_numpy()
    soc=energy/(caps['battery']/1000) if caps['battery']>1e-6 else energy*0
    capacity_violation=max(0,float((pv-n.generators.at['pv','p_nom_opt']*cf).max()),
                           float((charge+discharge-caps['converter']/1000).max()))
    soc_violation=max(0,float((CONFIG['battery_min_soc']*caps['battery']/1000-energy).max()),
                        float((energy-CONFIG['battery_max_soc']*caps['battery']/1000).max()))
    grid_outage=max(0,float((grid-CONFIG['grid_tie_capacity_kW']/1000*grid_availability).max())) if mode=='grid_extension' else 0
    # No load shedding component: every load must be served in the mathematical solution.
    checks=dict(max_power_balance_error_MW=float(balance.abs().max()),
                max_storage_balance_error_MWh=float(np.max(np.abs(storage_residual))),
                capacity_violation_MW=capacity_violation,soc_violation_MWh=soc_violation,
                grid_availability_violation_MW=grid_outage,
                diesel_budget_violation_MWh=max(0,float(diesel.sum()-fuel_limit)),
                annual_cost_objective_gap_USD=float(objective_gap),
                simultaneous_charge_discharge_MWh=float(np.minimum(charge,discharge).sum()))
    assert checks['max_power_balance_error_MW']<1e-6,checks
    assert checks['max_storage_balance_error_MWh']<1e-6,checks
    assert max(capacity_violation,soc_violation,grid_outage,checks['diesel_budget_violation_MWh'])<1e-6,checks
    assert abs(objective_gap)<.05,checks
    assert checks['simultaneous_charge_discharge_MWh']<1e-4,checks
    run_id=f'{site.geohash}_{mode}_{scenario}'
    OUT.mkdir(parents=True,exist_ok=True)
    hourly=pd.DataFrame(dict(target_delivered_MW=delivered,bus_load_MW=load,pv_MW=pv,diesel_MW=diesel,grid_MW=grid,
                             charge_MW=charge,discharge_MW=discharge,battery_MWh=energy,battery_soc=soc,pv_available_pu=cf,
                             grid_available_pu=grid_availability),index=n.snapshots)
    hourly.index.name='time_UTC'
    hourly.to_csv(OUT/f'{run_id}_hourly.csv.gz',compression={'method':'gzip','mtime':0},lineterminator='\n')
    record=dict(run_id=run_id,geohash=site.geohash,pilot_type=site.pilot_type,source_name=site.village_name,
                state=site.admin_cgaz_1,mode=mode,scenario=scenario,service_points=count,
                demand_multiplier=multiplier,annual_delivered_kWh=delivered.sum()*1000,peak_delivered_kW=delivered.max()*1000,
                pv_kWp=caps['pv'],battery_nominal_kWh=caps['battery'],converter_AC_kW=caps['converter'],diesel_kW=caps['diesel'],
                pv_generation_kWh=pv.sum()*1000,diesel_generation_kWh=diesel.sum()*1000,grid_import_kWh=grid.sum()*1000,
                pv_yield_proxy_kWh_per_kWp=cf.sum(),atlas_longrun_yield_kWh_per_kWp=site.pv_value,
                new_MV_route_proxy_km=q['mv_line'],LV_route_proxy_km=q['lv_line'],
                initial_budget_USD=actual['summary']['initial_budget_USD'],lifecycle_NPC_USD=npc,equivalent_annual_cost_USD=eac,
                modelled_LCOE_USD_per_kWh=eac/(delivered.sum()*1000),
                annual_operating_USD=sum(actual['operating'].values())-sum(actual['operating'][x] for x in yearly)+sum(yearly.values()),
                unserved_energy_kWh=max(0,float((-balance).clip(lower=0).sum())*1000),
                status='optimal_under_assumptions',field_validation='none',**checks)
    actual_items=[dict(run_id=run_id,**item) for item in actual['items']]
    cash=[dict(run_id=run_id,**row) for row in actual['ledger']]
    print(f"{run_id}: PV {caps['pv']:.1f} kWp, battery {caps['battery']:.1f} kWh, ${record['modelled_LCOE_USD_per_kWh']:.3f}/kWh",flush=True)
    return record,actual_items,cash


def run(force=False, base_only=False):
    marker=OUT/'run_manifest.json'
    current=fingerprint()
    if not force and marker.exists():
        previous=json.loads(marker.read_text())
        integrity=all((OUT/name).is_file() and hashlib.sha256((OUT/name).read_bytes()).hexdigest()==digest
                      for name,digest in previous.get('output_hashes',{}).items())
        if previous.get('inputs')==current and integrity and previous.get('complete'):
            print('Using checked cached optimization outputs; set FORCE_PILOT=True to solve again.')
            return pd.read_csv(OUT/'summary.csv')
    sites=pd.read_csv(DATA/'sites.csv')
    tasks=[(s,m,'base') for s in sites.itertuples(index=False) for m in MODES]
    if not base_only:
        tasks +=[(s,'grid_extension','evening_outage') for s in sites.itertuples(index=False)]
        tasks +=[(s,'mini_grid','no_diesel') for s in sites.itertuples(index=False)]
        dense=next(s for s in sites.itertuples(index=False) if s.pilot_type=='remote_dense')
        tasks +=[(dense,m,'double_demand') for m in MODES]
    records=[];items=[];cash=[]
    for site,mode,scenario in tasks:
        rec,ii,cc=solve(site,mode,scenario);records.append(rec);items.extend(ii);cash.extend(cc)
    summary=pd.DataFrame(records)
    summary.to_csv(OUT/'summary.csv',index=False,lineterminator='\n')
    pd.DataFrame(items).to_csv(OUT/'selected_components.csv',index=False,lineterminator='\n')
    pd.DataFrame(cash).to_csv(OUT/'lifecycle_cashflows.csv',index=False,lineterminator='\n')
    keys=['run_id']+[k for k in summary if 'violation' in k or 'error' in k or 'gap_USD' in k or 'simultaneous_' in k]
    summary[keys].to_csv(OUT/'checks.csv',index=False,lineterminator='\n')
    files=[OUT/f'{rec["run_id"]}_hourly.csv.gz' for rec in records]
    files += [OUT/x for x in ('summary.csv','selected_components.csv','lifecycle_cashflows.csv','checks.csv')]
    hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    marker.write_text(json.dumps(dict(inputs=current,output_hashes=hashes,complete=not base_only,runs=len(summary),
                          pypsa_version=pypsa.__version__,weather_year=2022,
                          status='Optimality and numerical consistency under provisional assumptions; no field validation'),indent=2)+'\n',encoding='utf-8')
    return summary


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--force',action='store_true');parser.add_argument('--base-only',action='store_true')
    args=parser.parse_args();run(force=args.force,base_only=args.base_only)
