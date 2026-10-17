"""Select a state-spanning source sample and explicitly cache NASA POWER weather."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import argparse, hashlib, json, time
import numpy as np
import pandas as pd
import requests

ROOT=Path(__file__).resolve().parents[2]
DATA=ROOT/'data/spatial_proxy_study'
SOURCE=ROOT/'research/dre_atlas_2025/data/settlement_attributes.csv.gz'
DESIGN=json.loads((DATA/'design.json').read_text())

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def select():
    d=pd.read_csv(SOURCE);cfg=DESIGN['selection']
    numeric=cfg['features']+['demand','building_density_percent']
    valid=np.isfinite(d[numeric]).all(axis=1)
    eligible=valid & d.admin_cgaz_1.notna() & d.num_connections.between(cfg['minimum_connections'],cfg['maximum_connections'])
    eligible &= (d.hull_area>0)&d.building_density_percent.between(0,cfg['maximum_building_density_percent'])&(d.demand>0)
    eligible &= (d.pv_value>0)&(d.distance_to_existing_transmission_lines>=0)
    if cfg['require_no_detected_nightlight']:eligible &= ~d.has_nightlight
    e=d.loc[eligible].copy();sites=[];coverage=[]
    for state,g in e.groupby('admin_cgaz_1',sort=True):
        f=g[cfg['features']].copy()
        f[cfg['log1p_features']]=np.log1p(f[cfg['log1p_features']])
        spread=(f.quantile(.75)-f.quantile(.25)).replace(0,1)
        score=(((f-f.median())/spread)**2).sum(axis=1)
        candidate=g.assign(selection_score=score).sort_values(['selection_score','geohash']).iloc[0].copy()
        candidate['pilot_type']='state_sample';candidate['sample_id']=len(sites)+1
        candidate['grid_in_local_scope']=bool(candidate.distance_to_existing_transmission_lines<=DESIGN['grid_max_straight_distance_km'])
        candidate['atlas_daily_kWh_per_connection']=candidate.demand/candidate.num_connections
        candidate['recomputed_building_demand_kWh_day']=1.1*candidate.large_buildings+.65*candidate.medium_buildings+.335*candidate.small_buildings
        assert abs(candidate['recomputed_building_demand_kWh_day']-candidate.demand)<=.050001
        sites.append(candidate)
        coverage.append(dict(state=state,atlas_clusters=int((d.admin_cgaz_1==state).sum()),eligible_clusters=len(g),selected_clusters=1,
                    selected_geohash=candidate.geohash,grid_in_local_scope=candidate.grid_in_local_scope,
                    eligible_median_grid_distance_km=g.distance_to_existing_transmission_lines.median()))
    assert len(sites)==18 and len({r.geohash for r in sites})==18
    cols=['sample_id','pilot_type','geohash','village_name','admin_cgaz_1','admin_cgaz_2','lat','lon','num_connections','num_buildings',
          'large_buildings','medium_buildings','small_buildings','demand','demand_connection','atlas_daily_kWh_per_connection',
          'recomputed_building_demand_kWh_day','hull_area','building_density_percent','distance_to_existing_transmission_lines',
          'pv_value','has_nightlight','selection_score','grid_in_local_scope']
    sites=pd.DataFrame(sites)[cols]
    DATA.mkdir(parents=True,exist_ok=True)
    sites.to_csv(DATA/'sites.csv',index=False,lineterminator='\n')
    pd.DataFrame(coverage).to_csv(DATA/'coverage.csv',index=False,lineterminator='\n')
    d[['geohash','lat','lon']].to_csv(DATA/'atlas_context_points.csv.gz',index=False,compression={'method':'gzip','mtime':0},lineterminator='\n')
    provenance=dict(atlas_clusters=len(d),eligible_clusters=len(e),selected_clusters=len(sites),states_selected=18,
       missing_state_clusters=int(d.admin_cgaz_1.isna().sum()),source_file=SOURCE.relative_to(ROOT).as_posix(),source_sha256=sha(SOURCE),
       licence='World Bank Group / VIDA DRE Atlas 2025 release, CC BY 4.0',
       source_url='https://energydata.info/dataset/sudan-distributed-renewable-energy-dre',
       selection=cfg,selected_file_sha256=sha(DATA/'sites.csv'),coverage_file_sha256=sha(DATA/'coverage.csv'),
       context_points_sha256=sha(DATA/'atlas_context_points.csv.gz'),
       note='Geographic breadth only: one deterministic median-profile cluster per state, not random sampling or state representation. No inference of present access or safety.')
    (DATA/'selection_manifest.json').write_text(json.dumps(provenance,indent=2)+'\n',encoding='utf-8')
    print(sites[['sample_id','admin_cgaz_1','geohash','num_connections','demand','distance_to_existing_transmission_lines','grid_in_local_scope']].to_string(index=False),flush=True)
    return sites

def fetch(row):
    target=DATA/f'weather_{row.geohash}_2022.csv.gz';metadata=DATA/f'weather_{row.geohash}_source.json'
    if target.exists() and metadata.exists():
        old=json.loads(metadata.read_text())
        if sha(target)==old['file_sha256']:return old
    params=dict(parameters='ALLSKY_SFC_SW_DWN,T2M',community='RE',longitude=row.lon,latitude=row.lat,
                start='20220101',end='20221231',format='JSON',**{'time-standard':'UTC'})
    for attempt in range(3):
        try:
            response=requests.get('https://power.larc.nasa.gov/api/temporal/hourly/point',params=params,timeout=180)
            response.raise_for_status();raw=response.json()
            frame=pd.DataFrame(raw['properties']['parameter'])
            frame.index=pd.to_datetime(frame.index,format='%Y%m%d%H');frame.index.name='time_UTC'
            assert frame.index.equals(pd.date_range('2022-01-01',periods=8760,freq='h'))
            assert frame.notna().all().all() and (frame.ALLSKY_SFC_SW_DWN>=0).all() and (frame.T2M>-80).all()
            unit=raw['parameters']['ALLSKY_SFC_SW_DWN']['units'].lower().replace(' ','')
            assert unit in ('wh/m^2','w/m^2'),unit
            frame.to_csv(target,compression={'method':'gzip','mtime':0},lineterminator='\n')
            meta=dict(geohash=row.geohash,url=response.url,raw_sha256=hashlib.sha256(response.content).hexdigest(),
                      file=target.name,file_sha256=sha(target),rows=8760,parameters=raw['parameters'],
                      geometry=raw.get('geometry'),header=raw.get('header'),downloaded='2026-10-17')
            metadata.write_text(json.dumps(meta,indent=2)+'\n',encoding='utf-8')
            print(f'Cached complete hourly weather: {row.admin_cgaz_1} / {row.geohash}',flush=True)
            return meta
        except (requests.RequestException,ValueError) as error:
            if attempt==2:raise
            print(f'Retrying {row.geohash}: {type(error).__name__}',flush=True);time.sleep(5*(attempt+1))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--selection-only',action='store_true');args=p.parse_args()
    sites=select()
    if not args.selection_only:
        with ThreadPoolExecutor(max_workers=3) as pool:weather=list(pool.map(fetch,sites.itertuples(index=False)))
        (DATA/'weather_manifest.json').write_text(json.dumps(dict(weather=weather,year=2022,time_standard='UTC',
             interpretation='NASA POWER gridded weather, not station validation; source hourly Wh/m2 numerically equals average W/m2 for the hourly interval'),indent=2)+'\n',encoding='utf-8')
