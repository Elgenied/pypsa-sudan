"""Select three illustrative DRE clusters and fetch 2022 NASA POWER hourly weather.

Run explicitly to refresh inputs. The notebook runs from cached input data, offline.
"""
from pathlib import Path
import hashlib, json
from concurrent.futures import ThreadPoolExecutor
import requests
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[2]
DATA=ROOT/'data/electrification_pilot'
DATA.mkdir(parents=True,exist_ok=True)
source=ROOT/'research/dre_atlas_2025/data/settlement_attributes.csv.gz'
d=pd.read_csv(source)
eligible=d[d.num_connections.between(80,250) & d.admin_cgaz_1.notna() & d.village_name.notna()
           & ~d.village_name.str.startswith('Location',na=False) & (d.hull_area>0)
           & (d.building_density_percent<25) & ~d.has_nightlight].copy()
near=eligible[eligible.distance_to_existing_transmission_lines.between(1,3)].sort_values('geohash').iloc[0].copy()
remote=eligible[eligible.distance_to_existing_transmission_lines.between(15,35)]
dense=remote[remote.building_density_percent>10].sort_values(['building_density_percent','geohash'],ascending=[False,True]).iloc[0].copy()
sparse=remote[remote.building_density_percent<2].sort_values(['building_density_percent','geohash']).iloc[0].copy()
sites=pd.DataFrame([near,dense,sparse])
sites.insert(0,'pilot_type',['near_grid','remote_dense','remote_sparse'])
cols=['pilot_type','geohash','village_name','admin_cgaz_1','admin_cgaz_2','lat','lon','num_connections',
      'demand','hull_area','building_density_percent','distance_to_existing_transmission_lines','pv_value','has_nightlight']
sites=sites[cols]
sites.to_csv(DATA/'sites.csv',index=False,lineterminator='\n')
print(sites[['pilot_type','geohash','village_name','admin_cgaz_1']].to_string(index=False),flush=True)

def fetch(row):
    params=dict(parameters='ALLSKY_SFC_SW_DWN,T2M',community='RE',longitude=row.lon,latitude=row.lat,
                start='20220101',end='20221231',format='JSON',**{'time-standard':'UTC'})
    r=requests.get('https://power.larc.nasa.gov/api/temporal/hourly/point',params=params,timeout=180)
    r.raise_for_status();raw=r.json()
    obs=raw['properties']['parameter']
    frame=pd.DataFrame(obs)
    frame.index=pd.to_datetime(frame.index,format='%Y%m%d%H');frame.index.name='time_UTC'
    expected=pd.date_range('2022-01-01',periods=8760,freq='h')
    assert frame.index.equals(expected) and frame.notna().all().all()
    assert (frame.ALLSKY_SFC_SW_DWN>=0).all() and (frame.T2M>-80).all()
    units=raw['parameters']['ALLSKY_SFC_SW_DWN']['units']
    assert units.lower().replace(' ','') in ('wh/m^2','w/m^2'),units
    path=DATA/f'weather_{row.geohash}_2022.csv.gz'
    frame.to_csv(path,compression={'method':'gzip','mtime':0},lineterminator='\n')
    return dict(geohash=row.geohash,url=r.url,raw_sha256=hashlib.sha256(r.content).hexdigest(),
                file=path.name,file_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                parameters=raw['parameters'],header=raw.get('header'),geometry=raw.get('geometry'),
                downloaded='2026-10-17',rows=len(frame))

with ThreadPoolExecutor(max_workers=3) as pool:
    provenance=list(pool.map(fetch,sites.itertuples(index=False)))
manifest=dict(attribution='World Bank Group / VIDA DRE Atlas (CC BY 4.0); NASA POWER hourly radiation and temperature',
              dre_source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
              selection='Named clusters; 80-250 potential connections; no detected nightlight; positive area; density <25%. Near: 1-3 km to grid, first geohash. Remote: 15-35 km; highest density >10%, lowest density <2%; ties by geohash. No cost-based selection.',
              limitations='Names are reverse-geocoded labels; buildings are not customers; absent nightlights do not prove lack of access; grid distances are not surveyed routes; this is not a representative or safe-site sample.',
              weather=provenance)
(DATA/'source_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
config=dict(weather_year=2022,horizon_years=20,daily_kWh_per_service_point=1,local_UTC_offset_hours=2,
            hourly_demand_weights=[.25,.2,.2,.2,.2,.3,.6,.8,.6,.5,.5,.6,.7,.6,.6,.7,1,1.8,2.8,3.2,2.6,1.6,.8,.4],
            pv_misc_dc_efficiency=.9,pv_inverter_efficiency=.96,pv_temperature_coefficient=-.004,pv_NOCT_C=45,
            battery_charge_efficiency=.95,battery_discharge_efficiency=.95,battery_min_soc=.1,battery_max_soc=.9,
            mv_route_factor=1.3,lv_length_factor=1.3,mini_grid_distribution_loss=.08,grid_distribution_loss=.10,
            standalone_hardware_markup=1.25,diesel_max_fraction_of_delivered_energy=.2,
            outage_local_hours=[18,19,20,21,22,23],grid_tie_capacity_kW=80,
            pv_capacity_limit_kWp_per_service_point=5,battery_limit_kWh_per_service_point=30,
            converter_limit_kW_per_service_point=5,diesel_limit_kW_per_service_point=2,
            assumptions_status='All design, route, demand, efficiency, reliability and price inputs provisional. No post-war field validation.')
(DATA/'config.json').write_text(json.dumps(config,indent=2)+'\n',encoding='utf-8')
print('Fetched and validated three complete 8760-hour weather series.',flush=True)
