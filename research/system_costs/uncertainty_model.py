"""Re-optimized exploratory sensitivities using the unchanged, checked pilot engine.

Scenario contexts are sequential and always restored; do not call from threads.
Independent processes are safe. Route-only changes are exact fixed-cost offsets
under the pilot's constant losses and fixed tie-in, explicitly not new routing.
"""
from pathlib import Path
from contextlib import contextmanager
import argparse, copy, hashlib, itertools, json, shutil, time
from concurrent.futures import ProcessPoolExecutor
from types import SimpleNamespace
import numpy as np
import pandas as pd
import pilot_model as pilot
from cost_model import load_inputs as original_inputs, annuity

ROOT=pilot.ROOT
DATA=ROOT/'data/electrification_uncertainty'
OUT=Path(__file__).resolve().parent/'results/uncertainty'
DESIGN=json.loads((DATA/'design.json').read_text())
BASE_CONFIG=copy.deepcopy(pilot.CONFIG)
MODES=pilot.MODES
PRICE='modelled_LCOE_USD_per_kWh'
PARAMS={'discount_rate':'real_discount_rate','diesel_price':'diesel_delivered_price','grid_price':'bulk_grid_supply'}
CENTRAL={k:v['central'] for k,v in DESIGN['axes'].items()}

def sha(path):
    p=Path(path);b=p.read_bytes()
    return hashlib.sha256(b if p.suffix=='.gz' else b.replace(b'\r\n',b'\n')).hexdigest()

def fingerprints():
    out=pilot.fingerprint()
    for p in [Path(__file__),DATA/'design.json']:
        out[p.relative_to(ROOT).as_posix()]=sha(p)
    return out

def effective(mode, changes):
    unknown=set(changes)-set(CENTRAL)
    if unknown:raise ValueError(f'Unknown assumptions: {unknown}')
    c={k:float(v) for k,v in changes.items() if not np.isclose(v,CENTRAL[k],rtol=0,atol=1e-12)}
    for key,allowed in {'diesel_price':['mini_grid'],'grid_price':['grid_extension'],
                        'outage_hours':['grid_extension'],'mv_cost_factor':['grid_extension'],
                        'standalone_markup':['standalone'],'lv_length_factor':['mini_grid','grid_extension']}.items():
        if mode not in allowed:c.pop(key,None)
    return c

@contextmanager
def context(changes, output=None):
    """Apply assumptions in memory only; preserve published baseline files/globals."""
    previous_config=pilot.CONFIG;previous_inputs=pilot.load_inputs;previous_out=pilot.OUT
    config=copy.deepcopy(BASE_CONFIG)
    config['daily_kWh_per_service_point']=changes.get('daily_kWh',CENTRAL['daily_kWh'])
    config['standalone_hardware_markup']=changes.get('standalone_markup',CENTRAL['standalone_markup'])
    config['lv_length_factor']*=changes.get('lv_length_factor',1)
    hours=int(changes.get('outage_hours',0))
    assert hours==changes.get('outage_hours',0) and 0<=hours<=24
    config['outage_local_hours']=[(18+i)%24 for i in range(hours)]
    def inputs():
        data=copy.deepcopy(original_inputs())
        for k,p in PARAMS.items():
            if k in changes:data[1][p]['central']=changes[k]
        for factor,parts in {'pv_cost_factor':['pv_module','pv_bos','pv_inverter'],
                             'battery_cost_factor':['battery'],'mv_cost_factor':['mv_line']}.items():
            for component in parts:
                for field in ('low_USD','base_USD','high_USD'):
                    data[0][component][field]*=changes.get(factor,1)
        return data
    try:
        pilot.CONFIG=config;pilot.load_inputs=inputs
        if output is not None:pilot.OUT=Path(output)
        yield
    finally:
        pilot.CONFIG=previous_config;pilot.load_inputs=previous_inputs;pilot.OUT=previous_out

def case_id(site,mode,changes):
    key=json.dumps(dict(geohash=site.geohash,mode=mode,changes=effective(mode,changes)),sort_keys=True)
    return hashlib.sha256(key.encode()).hexdigest()[:16]

def evaluate_case(site, mode, changes=None):
    changes=effective(mode,changes or {})
    cid=case_id(site,mode,changes);folder=OUT/'cases'/cid;marker=folder/'case.json'
    inputs=fingerprints()
    if marker.exists():
        old=json.loads(marker.read_text())
        if old['inputs']==inputs and all((folder/p).exists() and sha(folder/p)==h for p,h in old['outputs'].items()):
            return old['record']
    folder.mkdir(parents=True,exist_ok=True)
    # Reuse only the identical published base problem, with its manifest verified.
    reused=False
    if not changes:
        manifest=json.loads((pilot.OUT/'run_manifest.json').read_text())
        assert manifest['inputs']==pilot.fingerprint()
        assert all(sha(pilot.OUT/n)==h for n,h in manifest['output_hashes'].items())
        base=pd.read_csv(pilot.OUT/'summary.csv')
        row=base[(base.geohash==site.geohash)&(base['mode']==mode)&(base.scenario=='base')].iloc[0]
        rec=row.to_dict();source=pilot.OUT/(rec['run_id']+'_hourly.csv.gz')
        shutil.copy2(source,folder/'hourly.csv.gz');reused=True
    else:
        with context(changes,folder):
            rec,_,_=pilot.solve(site,mode,'evening_outage' if changes.get('outage_hours',0)>0 else 'base')
        generated=folder/(rec['run_id']+'_hourly.csv.gz')
        generated.replace(folder/'hourly.csv.gz')
    rec.update(case_id=cid,assumptions_json=json.dumps(changes,sort_keys=True),baseline_reused=reused)
    # Check capacity bounds, not only feasibility; truncation would compromise sensitivities.
    bounds={'pv_kWp':'pv_capacity_limit_kWp_per_service_point','battery_nominal_kWh':'battery_limit_kWh_per_service_point',
            'converter_AC_kW':'converter_limit_kW_per_service_point','diesel_kW':'diesel_limit_kW_per_service_point'}
    rec['design_bound_binding']=any(rec[k]>=rec['service_points']*BASE_CONFIG[v]*.999 for k,v in bounds.items())
    if rec['design_bound_binding']:raise RuntimeError(f'Artificial design bound binds: {cid}')
    marker.write_text(json.dumps(dict(inputs=inputs,outputs={'hourly.csv.gz':sha(folder/'hourly.csv.gz')},
                      record=rec),indent=2)+'\n',encoding='utf-8')
    print(f'Checked case {cid}: {site.geohash} {mode} {changes}',flush=True)
    return rec

def fixed_annual(site, mode, changes):
    with context(effective(mode,changes)):
        return pilot.cost_context(site,mode)[3]

def fixed_adjusted(site,mode,changes):
    """MV cost/LV length cannot change optimal dispatch in this fixed-loss model."""
    operating={k:v for k,v in changes.items() if k not in ('mv_cost_factor','lv_length_factor')}
    rec=dict(evaluate_case(site,mode,operating))
    delta=fixed_annual(site,mode,changes)-fixed_annual(site,mode,operating)
    rec['equivalent_annual_cost_USD']+=delta
    rec[PRICE]=rec['equivalent_annual_cost_USD']/rec['annual_delivered_kWh']
    with context(effective(mode,changes)):
        _,q,ledger,_,_,_=pilot.cost_context(site,mode)
        fixed_new=ledger(q)
        rec['new_MV_route_proxy_km']=q['mv_line'];rec['LV_route_proxy_km']=q['lv_line']
    with context(effective(mode,operating)):
        _,q,ledger,_,_,_=pilot.cost_context(site,mode)
        fixed_old=ledger(q)
    rec['initial_budget_USD']+=fixed_new['summary']['initial_budget_USD']-fixed_old['summary']['initial_budget_USD']
    rec['annual_operating_USD']+=sum(fixed_new['operating'].values())-sum(fixed_old['operating'].values())
    params=fixed_new['parameters']
    rec['lifecycle_NPC_USD']=rec['equivalent_annual_cost_USD']/annuity(params['real_discount_rate'],params['horizon_years'])
    rec['scenario_assumptions_json']=json.dumps(changes,sort_keys=True)
    rec['evaluation']='exact_fixed_cost_adjustment' if abs(delta)>1e-9 else 'optimized_or_identical_cache'
    rec['fixed_annual_adjustment_USD']=delta
    return rec

def write_table(name,rows):
    p=OUT/name;p.parent.mkdir(parents=True,exist_ok=True)
    pd.DataFrame(rows).to_csv(p,index=False,lineterminator='\n')

def solve_worker(task):
    site,mode,changes=task
    return evaluate_case(SimpleNamespace(**site),mode,changes)['case_id']

def prepare_cases(sites):
    """Solve independent cases in separate processes; never share scenario globals."""
    tasks={}
    def add(s,m,c):
        c={k:v for k,v in c.items() if k not in ('mv_cost_factor','lv_length_factor')}
        tasks[case_id(s,m,c)]=(s._asdict(),m,c)
    for axis,spec in DESIGN['axes'].items():
        for value in spec['values']:
            for s in sites:
                for mode in MODES:add(s,mode,{axis:value})
    j=DESIGN['joint_design']
    for demand,hardware,outage in itertools.product(j['daily_kWh'],j['hardware_bundles'].values(),j['outage_hours']):
        for s in sites:
            for mode in MODES:add(s,mode,dict(daily_kWh=demand,outage_hours=outage,**hardware))
    current=fingerprints();pending=[]
    for cid,task in tasks.items():
        p=OUT/'cases'/cid/'case.json'
        if p.exists():
            m=json.loads(p.read_text())
            if m['inputs']==current and all((p.parent/f).exists() and sha(p.parent/f)==h for f,h in m['outputs'].items()):continue
        pending.append(task)
    print(f'Independent case pool: {len(pending)} pending, {len(tasks)} unique before threshold refinement',flush=True)
    if pending:
        with ProcessPoolExecutor(max_workers=3) as pool:
            for i,_ in enumerate(pool.map(solve_worker,pending),1):
                print(f'Pool progress {i}/{len(pending)}',flush=True)

def run():
    sites=list(pd.read_csv(pilot.DATA/'sites.csv').itertuples(index=False))
    prepare_cases(sites)
    rows=[]
    for axis,spec in DESIGN['axes'].items():
        for value in spec['values']:
            for s in sites:
                for mode in MODES:
                    r=fixed_adjusted(s,mode,{axis:value})
                    rows.append(dict(axis=axis,value=value,**r))
        write_table('one_at_a_time.csv',rows)
        print(f'Completed sensitivity: {axis}',flush=True)
    joint=[];j=DESIGN['joint_design']
    for demand,(bundle,hardware),outage in itertools.product(j['daily_kWh'],j['hardware_bundles'].items(),j['outage_hours']):
        scenario=f'demand_{demand:g}_hardware_{bundle}_outage_{outage}'
        changes=dict(daily_kWh=demand,outage_hours=outage,**hardware)
        for s in sites:
            for mode in MODES:
                r=evaluate_case(s,mode,changes)
                joint.append(dict(joint_scenario=scenario,scenario_assumptions_json=json.dumps(changes,sort_keys=True),**r))
        write_table('joint_scenarios.csv',joint)
        print(f'Completed joint scenario: {scenario}',flush=True)
    # Exact route threshold under constant loss and tie-in assumptions.
    routes=[];thresholds=[]
    for s in sites:
        for outage in [0,3,6,9]:
            changes={'outage_hours':outage}
            grid=evaluate_case(s,'grid_extension',changes)
            local=[evaluate_case(s,m) for m in ('standalone','mini_grid')]
            best=min(local,key=lambda r:r['equivalent_annual_cost_USD'])
            s0=s._replace(distance_to_existing_transmission_lines=0.)
            s1=s._replace(distance_to_existing_transmission_lines=1./BASE_CONFIG['mv_route_factor'])
            f0=fixed_annual(s0,'grid_extension',changes)
            slope=fixed_annual(s1,'grid_extension',changes)-f0
            zero=grid['equivalent_annual_cost_USD']-fixed_annual(s,'grid_extension',changes)+f0
            root=(best['equivalent_annual_cost_USD']-zero)/slope
            thresholds.append(dict(geohash=s.geohash,source_name=s.village_name,outage_hours=outage,
                  best_offgrid=best['mode'],grid_zero_route_annual_USD=zero,offgrid_annual_USD=best['equivalent_annual_cost_USD'],
                  MV_annual_USD_per_route_km=slope,break_even_new_MV_route_km=root if root>=0 else np.nan,
                  status='nonnegative_crossing' if root>=0 else 'grid_more_expensive_even_at_zero_route',
                  assumed_route_km=BASE_CONFIG['mv_route_factor']*s.distance_to_existing_transmission_lines))
            for km in DESIGN['route_curve_km']:
                routes.append(dict(geohash=s.geohash,outage_hours=outage,new_MV_route_km=km,
                  grid_LCOE=(zero+slope*km)/grid['annual_delivered_kWh'],
                  standalone_LCOE=local[0][PRICE],mini_grid_LCOE=local[1][PRICE]))
    write_table('route_thresholds.csv',thresholds);write_table('route_curves.csv',routes)
    # Locate all observed sign changes for mini-grid versus standalone, using full solves.
    # No claim of global monotonicity or uniqueness outside searched intervals.
    breaks=[];oat=pd.DataFrame(rows)
    for s in sites:
        def gap(d):
            a=evaluate_case(s,'mini_grid',{'daily_kWh':d});b=evaluate_case(s,'standalone',{'daily_kWh':d})
            return a[PRICE]-b[PRICE]
        xs=DESIGN['axes']['daily_kWh']['values']
        found=False
        for lo,hi in zip(xs[:-1],xs[1:]):
            a,b=gap(lo),gap(hi)
            if a*b>0:continue
            found=True
            for _ in range(DESIGN['demand_break_even_max_iterations']):
                if hi-lo<=DESIGN['demand_break_even_tolerance_kWh_day']:break
                mid=(lo+hi)/2;g=gap(mid)
                if a*g<=0:hi,b=mid,g
                else:lo,a=mid,g
            breaks.append(dict(geohash=s.geohash,source_name=s.village_name,lower_kWh_day=lo,upper_kWh_day=hi,
                              lower_mini_minus_standalone_USD_kWh=a,upper_mini_minus_standalone_USD_kWh=b,
                              status='sign_change_bracket'))
        if not found:
            breaks.append(dict(geohash=s.geohash,source_name=s.village_name,lower_kWh_day=xs[0],upper_kWh_day=xs[-1],
                              lower_mini_minus_standalone_USD_kWh=gap(xs[0]),upper_mini_minus_standalone_USD_kWh=gap(xs[-1]),
                              status='no_sign_change_on_tested_grid'))
    write_table('demand_thresholds.csv',breaks)
    # All outputs, including independent case records, are content-addressed and audited.
    cases=[json.loads(p.read_text())['record'] for p in sorted((OUT/'cases').glob('*/case.json'))
           if json.loads(p.read_text())['inputs']==fingerprints()]
    write_table('optimized_cases.csv',cases)
    files=list((OUT/'cases').glob('*/*'))+list(OUT.glob('*.csv'))
    (OUT/'manifest.json').write_text(json.dumps(dict(inputs=fingerprints(),complete=True,
        unique_optimized_cases=len(cases),fresh_solves=sum(not r['baseline_reused'] for r in cases),
        outputs={p.relative_to(OUT).as_posix():sha(p) for p in files},
        interpretation='Exploratory scenarios, no probability distribution or field validation'),indent=2)+'\n',encoding='utf-8')
    return pd.DataFrame(rows),pd.DataFrame(joint)

def load_results(force=False):
    marker=OUT/'manifest.json'
    if not force and marker.exists():
        m=json.loads(marker.read_text())
        if m['inputs']==fingerprints() and m['complete'] and all((OUT/p).exists() and sha(OUT/p)==h for p,h in m['outputs'].items()):
            return pd.read_csv(OUT/'one_at_a_time.csv'),pd.read_csv(OUT/'joint_scenarios.csv')
    return run()

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--one',action='store_true');p.add_argument('--force',action='store_true')
    args=p.parse_args()
    if args.one:
        s=next(pd.read_csv(pilot.DATA/'sites.csv').itertuples(index=False))
        start=time.perf_counter();evaluate_case(s,'mini_grid',{'daily_kWh':.5})
        print(f'Elapsed {time.perf_counter()-start:.1f}s')
    else:load_results(force=args.force)
