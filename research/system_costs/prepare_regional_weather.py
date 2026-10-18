"""Cache one 2022 NASA POWER hourly point per planning zone; keep the state proxies for comparison."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from datetime import date
import argparse, json, time
import pandas as pd
import prepare_spatial_proxy as proxy
from prepare_regional_model import km, DATA, ROOT

BASE32='0123456789bcdefghjkmnpqrstuvwxyz'
POINT_RULE='connection_weighted_zone_centroid'

def geohash(lat,lon,precision=10):
    lat_range=[-90.,90.];lon_range=[-180.,180.];bits=[];even=True
    while len(bits)<precision*5:
        rng=lon_range if even else lat_range;value=lon if even else lat;mid=sum(rng)/2
        if value>=mid:bits.append(1);rng[0]=mid
        else:bits.append(0);rng[1]=mid
        even=not even
    return ''.join(BASE32[int(''.join(map(str,bits[i:i+5])),2)] for i in range(0,len(bits),5))

def table():
    state=pd.read_csv(DATA/'weather_proxies_state.csv').set_index('state');rows=[]
    for count in [36,48]:
        zones=pd.read_csv(DATA/f'zones_{count}.csv');cross=pd.read_csv(DATA/f'crosswalk_{count}.csv.gz')
        for z in zones.itertuples():
            members=cross[cross.zone_id.eq(z.zone_id)];lat,lon=round(float(z.lat),6),round(float(z.lon),6);g=geohash(lat,lon);s=state.loc[z.state]
            rows.append(dict(zones=count,zone_id=z.zone_id,state=z.state,point_rule=POINT_RULE,geohash=g,lat=lat,lon=lon,file=f'weather_{g}_2022.csv.gz',
                maximum_cluster_distance_km=float(km(members.lon,members.lat,lon,lat).max()),
                state_proxy_geohash=s.geohash,state_proxy_maximum_cluster_distance_km=float(km(members.lon,members.lat,s.lon,s.lat).max())))
    return pd.DataFrame(rows)

def prepare(workers=3):
    proxy.DATA=DATA  # reuse the spatial-proxy fetcher, caching beside the regional inputs
    t=table();points=t.drop_duplicates('geohash');started=time.time()
    sites=[SimpleNamespace(geohash=p.geohash,lat=p.lat,lon=p.lon,admin_cgaz_1=f'{p.state} {p.zone_id}') for p in points.itertuples()]
    with ThreadPoolExecutor(max_workers=workers) as pool:metas=list(pool.map(proxy.fetch,sites))
    for meta in metas:
        path=DATA/f"weather_{meta['geohash']}_source.json"
        if path.stat().st_mtime>=started:meta['downloaded']=date.today().isoformat();path.write_text(json.dumps(meta,indent=2)+'\n',encoding='utf-8')
    for p in points.itertuples():
        w=pd.read_csv(DATA/p.file);assert len(w)==8760 and w.ALLSKY_SFC_SW_DWN.ge(0).all()
    t.to_csv(DATA/'weather_proxies.csv',index=False,lineterminator='\n')
    (DATA/'weather_manifest.json').write_text(json.dumps(dict(point_rule=POINT_RULE,points=len(points),zone_rows=len(t),weather=metas,year=2022,time_standard='UTC',
        interpretation='NASA POWER gridded weather at each zone centroid, not station data; the six state points remain in weather_proxies_state.csv'),indent=2)+'\n',encoding='utf-8')
    print(t.groupby('zones').maximum_cluster_distance_km.describe().round(1).to_string(),flush=True);return t

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--workers',type=int,default=3);p.add_argument('--table-only',action='store_true');a=p.parse_args()
    print(table().to_string(index=False)) if a.table_only else prepare(a.workers)
