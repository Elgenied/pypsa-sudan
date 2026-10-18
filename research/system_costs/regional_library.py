"""Full-year candidate portfolios; scalable operations, explicit per-cluster fixed costs."""
from pathlib import Path
from types import SimpleNamespace
from contextlib import contextmanager
import copy,json
import numpy as np
import pandas as pd
import pilot_model as p
import recovery_model as r

ROOT=p.ROOT;DATA=ROOT/'data/regional_model';OUT=Path(__file__).resolve().parent/'results/regional/library'
CONFIG=json.loads((DATA/'config.json').read_text())

def inputs():
    x=r.inputs();x[1]['bulk_grid_supply']['central']=str(CONFIG['bulk_price_for_candidate_sizing_USD_MWh']/1000);return x

@contextmanager
def context(folder,sc=None):
    old=p.CONFIG,p.DATA,p.OUT,p.load_inputs
    p.CONFIG=copy.deepcopy(r.BASE);p.CONFIG.update(daily_kWh_per_service_point=1,grid_tie_capacity_kW=1000,
        outage_local_hours=CONFIG['scenarios'][sc]['outage_local_hours'] if sc else [])
    p.DATA=DATA;p.OUT=folder;p.load_inputs=inputs
    folder.mkdir(parents=True,exist_ok=True)
    try:yield
    finally:p.CONFIG,p.DATA,p.OUT,p.load_inputs=old

def fingerprints():
    files=list(DATA.glob('*'))+[Path(__file__),ROOT/'research/system_costs/pilot_model.py',ROOT/'research/system_costs/cost_model.py',ROOT/'research/system_costs/recovery_model.py',ROOT/'data/electrification_pilot/config.json']+list((ROOT/'data/system_costs').glob('*.csv'))
    return {x.relative_to(ROOT).as_posix():r.sha(x) for x in files if x.is_file()}

def valid(folder):
    path=folder/'manifest.json'
    if not path.exists():return False
    m=json.loads(path.read_text());return m['inputs']==fingerprints() and all((folder/x).exists() and r.sha(folder/x)==h for x,h in m['outputs'].items())

def stamp(folder,files):
    (folder/'manifest.json').write_text(json.dumps(dict(inputs=fingerprints(),outputs={x.relative_to(folder).as_posix():r.sha(x) for x in files}),indent=2)+'\n')

def run():
    OUT.mkdir(parents=True,exist_ok=True)
    if valid(OUT):return pd.read_csv(OUT/'summary.csv')
    rows=[]
    for w in pd.read_csv(DATA/'weather_proxies.csv').itertuples():
        site=SimpleNamespace(geohash=w.geohash,village_name=w.state,admin_cgaz_1=w.state,num_connections=1000,hull_area=1.,distance_to_existing_transmission_lines=0.,pv_value=1800.,pilot_type='regional_normalized_library')
        for mode,sc in [('standalone',None),('mini_grid',None)]+[('grid_extension',s) for s in CONFIG['scenarios']]:
            key=w.state.replace(' ','_')+'_'+(sc if sc else mode);folder=OUT/key
            if valid(folder):record=json.loads((folder/'record.json').read_text())
            else:
                print('Sizing full-year portfolio:',key,flush=True)
                with context(folder,sc):
                    record,_,_=p.solve(site,mode,'evening_outage' if sc else 'base')
                hourly=next(folder.glob('*hourly.csv.gz'))
                record.update(key=key,hourly_file=hourly.relative_to(OUT).as_posix())
                (folder/'record.json').write_text(json.dumps(record,indent=2)+'\n')
                stamp(folder,[folder/'record.json',hourly])
            rows.append(record)
    result=pd.DataFrame(rows);result.to_csv(OUT/'summary.csv',index=False,lineterminator='\n')
    stamp(OUT,[OUT/'summary.csv',*[x for x in OUT.rglob('*hourly.csv.gz')],*[x for x in OUT.rglob('record.json')]])
    return result

def package(zone,mode,scenario,library,demand_factor=1.,fuel_factor=1.):
    key=zone.state.replace(' ','_')+'_'+(scenario if mode=='grid' else mode)
    row=library.set_index('key').loc[key];scale=zone.target_MWh*demand_factor/365.
    site=SimpleNamespace(num_connections=zone.connections,hull_area=1.,distance_to_existing_transmission_lines=0.)
    pmode='grid_extension' if mode=='grid' else mode
    with context(OUT):
        _,q,ledger,_,_,groups=p.cost_context(site,pmode)
        # Existing wiring/distribution is sunk; charge only the assumed rehabilitation fraction.
        existing_fraction=zone.baseline_residential_MWh/(zone.target_MWh*demand_factor)
        rehabilitation=1-min(1,existing_fraction)*(1-CONFIG['existing_distribution_rehabilitation_fraction'])
        q['house_wiring']=zone.connections*rehabilitation
        if mode!='standalone':
            q.update(lv_line=zone.lv_km*(rehabilitation if mode=='grid' else 1),service_meter=zone.connections*rehabilitation,
                     civil_site=zone.clusters,land_right=zone.clusters,fuel_tank_ats=zone.clusters if mode=='mini_grid' else 0)
        if mode=='grid':
            q.update(mv_line=zone.mv_km*rehabilitation,transformer_100kVA=zone.transformer_units*demand_factor*rehabilitation,grid_protection=zone.clusters*rehabilitation)
        caps={k:float(row[k])*scale for k in ['pv_kWp','battery_nominal_kWh','converter_AC_kW','diesel_kW']}
        for asset,col in [('pv','pv_kWp'),('battery','battery_nominal_kWh'),('converter','converter_AC_kW'),('diesel','diesel_kW')]:
            for item in groups[asset]:q[item]=caps[col]
        actual=ledger(q)
    params={k:float(v['central']) for k,v in inputs()[1].items()}
    diesel_cost=row.diesel_generation_kWh*scale*(params['diesel_delivered_price']*params['diesel_specific_fuel']*fuel_factor+params['diesel_variable_om'])
    # The base ledger charges one network site. A zone contains separate cluster sites.
    site_security=0. if mode=='standalone' else zone.clusters*params['annual_security_network']
    extra_security=site_security-actual['operating']['security_allowance']
    return dict(zone_id=zone.zone_id,state=zone.state,supply_bus=zone.supply_bus,mode=mode,key=key,scale=scale,
        connections=zone.connections,clusters=zone.clusters,target_MWh=zone.target_MWh*demand_factor,
        local_EAC_USD=r.fixed_eac(actual)+diesel_cost+extra_security,initial_USD=actual['summary']['initial_budget_USD'],annual_site_security_USD=site_security,
        grid_import_MWh=row.grid_import_kWh*scale/1000,diesel_MWh=row.diesel_generation_kWh*scale/1000,**caps)

if __name__=='__main__':run()
