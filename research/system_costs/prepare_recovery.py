"""Freeze a small geographic demonstration before inspecting optimized choices."""
from pathlib import Path
import hashlib,json,shutil
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[2]
DATA=ROOT/'data/recovery_planning'
ANCHOR='scbmu9pc3u'

def distance(a,b):
    lat1,lat2=np.radians(a.lat),np.radians(b.lat)
    return 12742*np.arcsin(np.sqrt(np.sin((lat2-lat1)/2)**2+np.cos(lat1)*np.cos(lat2)*np.sin(np.radians(b.lon-a.lon)/2)**2))

def prepare():
    DATA.mkdir(parents=True,exist_ok=True)
    source=ROOT/'research/dre_atlas_2025/data/settlement_attributes.csv.gz'
    atlas=pd.read_csv(source);anchor=atlas.set_index('geohash').loc[ANCHOR]
    eligible=atlas.loc[(atlas.admin_cgaz_1=='Blue Nile') & atlas.num_connections.between(20,500)
        & (atlas.hull_area>0) & ~atlas.has_nightlight].copy()
    eligible['distance_to_anchor_km']=[distance(anchor,r) for r in eligible.itertuples()]
    sites=eligible.sort_values(['distance_to_anchor_km','geohash']).head(4).copy()
    sites['site_id']=['S1','S2','S3','S4'];sites['pilot_type']='neighbouring_recovery_cluster'
    columns=['site_id','geohash','village_name','admin_cgaz_1','admin_cgaz_2','lat','lon','num_connections',
        'hull_area','demand','distance_to_existing_transmission_lines','distance_to_anchor_km','pv_value','pilot_type']
    sites[columns].to_csv(DATA/'sites.csv',index=False,lineterminator='\n')
    edges=[];rows=list(sites.itertuples())
    for i,a in enumerate(rows):
        for b in rows[i+1:]:
            edges.append(dict(edge_id=a.site_id+'_'+b.site_id,from_site=a.site_id,to_site=b.site_id,
                route_km=1.3*distance(a,b),capacity_MW=.4,efficiency=.98,
                evidence='Candidate straight-line distance x1.3; unsurveyed new feeder'))
    pd.DataFrame(edges).to_csv(DATA/'candidate_routes.csv',index=False,lineterminator='\n')
    config=dict(study='Integrated Blue Nile recovery demonstration; not national allocation',
        daily_kWh_per_connection=1,weather_year=2022,weather_anchor_geohash=ANCHOR,
        weather_note='All four sites use the existing NASA POWER series at Al Kurumuk; maximum separation 2.21 km. No invented independent weather retrieval.',
        background_peak_MW=.03,background_note='Assumed separate existing feeder load, excluding all four candidate clusters; not an estimate of Blue Nile total demand.',
        upstream_repaired_capacity_MW=.15,common_feeder_capacity_MW=.4,common_feeder_efficiency=.98,
        common_feeder_repair_km=float(anchor.distance_to_existing_transmission_lines)*1.3,
        repair_fraction_of_new_line=.35,repair_note='Hypothetical repairable common feeder length from anchor atlas proximity x1.3. Neither an identified damaged line nor verified MV route.',
        regional_supply_cost_note='Existing ledger bulk-supply resource-service allowance at regional boundary. Additional repair cost restores access; historical sunk construction costs are excluded. No explicit national plant dispatch.',
        money_basis='constant 2025 USD, 20-year stationary service, 10% real discount; nonrecoverable tax set to zero for resource-cost comparison',
        scenario_order=['constrained','partial','broad'],
        scenarios=dict(constrained=dict(label='Constrained recovery',repair_budget_USD=0,existing_supply_MW=.04,outage_local_hours=[18,19,20,21,22,23]),
            partial=dict(label='Partial recovery',repair_budget_USD=30000,existing_supply_MW=.06,outage_local_hours=[19,20,21]),
            broad=dict(label='Broad recovery',repair_budget_USD=100000,existing_supply_MW=.08,outage_local_hours=[])),
        selection='Existing near-grid pilot anchor plus three nearest eligible Blue Nile clusters: 20-500 connections, positive area, no detected nightlight; ties geohash. No optimization outcome used.',
        reliability='Zero unmet modelled hourly load; no probabilistic outage or field reliability claim',
        mip_relative_gap=.0001)
    (DATA/'config.json').write_text(json.dumps(config,indent=2)+'\n')
    weather=ROOT/f'data/electrification_pilot/weather_{ANCHOR}_2022.csv.gz'
    for site in rows:shutil.copy2(weather,DATA/f'weather_{site.geohash}_2022.csv.gz')
    (DATA/'sources.json').write_text(json.dumps(dict(atlas_url='https://energydata.info/dataset/sudan-distributed-renewable-energy-dre',
        atlas_licence='World Bank Group / VIDA, CC BY 4.0',atlas_source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        weather_source=str(weather.relative_to(ROOT)),weather_sha256=hashlib.sha256(weather.read_bytes()).hexdigest(),
        weather_provenance='data/electrification_pilot/source_manifest.json',
        selection=config['selection'],maximum_weather_anchor_distance_km=float(sites.distance_to_anchor_km.max())),indent=2)+'\n')
    print(sites[columns].to_string(index=False))

if __name__=='__main__':prepare()
