"""State-spanning electrification scenarios using source building-demand proxies.

The pilot physics and cost ledger remain unchanged. Each independent solve has its
own full-year weather and identical delivered demand across supply alternatives.
No national weighting or extrapolation is performed.
"""
from pathlib import Path
from contextlib import contextmanager
from concurrent.futures import ProcessPoolExecutor
from types import SimpleNamespace
import argparse, copy, hashlib, json
import numpy as np
import pandas as pd
import pilot_model as pilot

ROOT=pilot.ROOT;DATA=ROOT/'data/spatial_proxy_study'
OUT=Path(__file__).resolve().parent/'results/spatial_proxy'
DESIGN=json.loads((DATA/'design.json').read_text())
BASE_CONFIG=copy.deepcopy(pilot.CONFIG)
PRICE='modelled_LCOE_USD_per_kWh'

def sha(path):
    p=Path(path);raw=p.read_bytes()
    return hashlib.sha256(raw if p.suffix=='.gz' else raw.replace(b'\r\n',b'\n')).hexdigest()

def fingerprints():
    paths=[Path(__file__),Path(__file__).with_name('pilot_model.py'),Path(__file__).with_name('cost_model.py'),
           Path(__file__).with_name('prepare_spatial_proxy.py'),ROOT/'data/electrification_pilot/config.json']
    paths+=list(DATA.glob('*.csv'))+list(DATA.glob('*.json'))+list(DATA.glob('*.gz'))
    paths+=list((ROOT/'data/system_costs').glob('*.csv'))
    return {p.relative_to(ROOT).as_posix():sha(p) for p in sorted(paths)}

def daily_demand(site,demand_case):
    value=DESIGN['demand_cases'][demand_case]['daily_kWh_per_connection']
    return float(site.demand/site.num_connections if value is None else value)

@contextmanager
def context(site,demand_case,outage_hours,output=None):
    old_config,old_data,old_out=pilot.CONFIG,pilot.DATA,pilot.OUT
    cfg=copy.deepcopy(BASE_CONFIG)
    cfg['daily_kWh_per_service_point']=daily_demand(site,demand_case)
    cfg['outage_local_hours']=[(18+i)%24 for i in range(int(outage_hours))]
    try:
        pilot.CONFIG=cfg;pilot.DATA=DATA
        if output is not None:pilot.OUT=Path(output)
        yield
    finally:pilot.CONFIG,pilot.DATA,pilot.OUT=old_config,old_data,old_out

def case_id(site,mode,demand_case,outage):
    return f'{site.geohash}_{mode}_{demand_case}_outage{outage}'

def task_list(sites):
    tasks=[]
    for site in sites:
        for demand in DESIGN['demand_cases']:
            tasks += [(site._asdict(),mode,demand,0) for mode in ['standalone','mini_grid']]
            if site.grid_in_local_scope:
                tasks +=[(site._asdict(),'grid_extension',demand,hours) for hours in DESIGN['grid_cases'].values()]
    return tasks

def solve_case(task):
    attrs,mode,demand_case,outage=task;site=SimpleNamespace(**attrs)
    cid=case_id(site,mode,demand_case,outage);folder=OUT/'cases'/cid;marker=folder/'case.json'
    current=fingerprints()
    if marker.exists():
        old=json.loads(marker.read_text())
        if old['inputs']==current and all((folder/p).exists() and sha(folder/p)==h for p,h in old['outputs'].items()):return old['record']
    folder.mkdir(parents=True,exist_ok=True)
    with context(site,demand_case,outage,folder):
        rec,_,_=pilot.solve(site,mode,'evening_outage' if outage else 'base')
    generated=folder/(rec['run_id']+'_hourly.csv.gz');generated.replace(folder/'hourly.csv.gz')
    rec.update(case_id=cid,run_id=cid,sample_id=site.sample_id,demand_case=demand_case,outage_hours=outage,
               daily_kWh_per_connection=daily_demand(site,demand_case),grid_in_local_scope=site.grid_in_local_scope,
               atlas_daily_demand_kWh=site.demand,atlas_connections=site.num_connections,
               direct_grid_distance_km=site.distance_to_existing_transmission_lines)
    bounds={'pv_kWp':'pv_capacity_limit_kWp_per_service_point','battery_nominal_kWh':'battery_limit_kWh_per_service_point',
            'converter_AC_kW':'converter_limit_kW_per_service_point','diesel_kW':'diesel_limit_kW_per_service_point'}
    rec['design_bound_binding']=any(rec[k]>=rec['service_points']*BASE_CONFIG[v]*.999 for k,v in bounds.items())
    if rec['design_bound_binding']:raise RuntimeError(f'Artificial design bound binds: {cid}')
    marker.write_text(json.dumps(dict(inputs=current,outputs={'hourly.csv.gz':sha(folder/'hourly.csv.gz')},record=rec),indent=2)+'\n',encoding='utf-8')
    print(f'Checked spatial case: {site.admin_cgaz_1} / {mode} / {demand_case} / outage {outage}',flush=True)
    return rec

def run(force=False):
    marker=OUT/'manifest.json';current=fingerprints()
    if not force and marker.exists():
        m=json.loads(marker.read_text())
        if m['complete'] and m['inputs']==current and all((OUT/p).exists() and sha(OUT/p)==h for p,h in m['outputs'].items()):
            return pd.read_csv(OUT/'summary.csv')
    sites=list(pd.read_csv(DATA/'sites.csv').itertuples(index=False));tasks=task_list(sites);rows=[]
    OUT.mkdir(parents=True,exist_ok=True)
    print(f'Running {len(tasks)} distinct full-year cases for {len(sites)} sampled clusters.',flush=True)
    with ProcessPoolExecutor(max_workers=DESIGN['worker_processes']) as pool:
        for i,row in enumerate(pool.map(solve_case,tasks),1):
            rows.append(row);print(f'Spatial progress {i}/{len(tasks)}',flush=True)
    result=pd.DataFrame(rows).sort_values(['sample_id','demand_case','mode','outage_hours'])
    result.to_csv(OUT/'summary.csv',index=False,lineterminator='\n')
    files=[OUT/'summary.csv']
    for r in rows:files.extend((OUT/'cases'/r['case_id']).glob('*'))
    marker.write_text(json.dumps(dict(complete=True,inputs=current,unique_hourly_cases=len(result),clusters=len(sites),
        outputs={p.relative_to(OUT).as_posix():sha(p) for p in files},
        interpretation='One illustrative selected cluster per state, conditional comparison among assessed options; no measured demand or national recommendation'),indent=2)+'\n',encoding='utf-8')
    return result

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--force',action='store_true');args=parser.parse_args();run(args.force)
