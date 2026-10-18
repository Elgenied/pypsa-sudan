"""Freeze six-state zones, accounting, weather proxies and candidate repairs."""
from pathlib import Path
import json, shutil
import numpy as np
import pandas as pd
import pypsa
from prepare_regional_scope import CORE
from recovery_model import sha

ROOT=Path(__file__).resolve().parents[2]
DATA=ROOT/'data/regional_model'
STATE_BUS={'Northern':['Dongola','Merowe'],'River Nile':['Atbara'],'Khartoum':['Khartoum'],
           'Gezira':['WadMedani'],'White Nile':['Kosti'],'Sennar':['Sennar']}

def km(lon,lat,x,y):
    a=np.radians(lat);b=np.radians(y)
    return 6371*2*np.arcsin(np.sqrt(np.clip(np.sin((a-b)/2)**2+np.cos(a)*np.cos(b)*np.sin(np.radians(lon-x)/2)**2,0,1)))

def zones(atlas,n,per_state):
    groups=[]
    for state in CORE:
        a=atlas[atlas.admin_cgaz_1.eq(state)].copy()
        buses=STATE_BUS[state]
        ds=np.column_stack([km(a.lon,a.lat,n.buses.at[b,'x'],n.buses.at[b,'y']) for b in buses])
        a['supply_bus']=np.asarray(buses)[ds.argmin(axis=1)]
        chunks=[g.copy() for _,g in a.groupby('supply_bus')]
        while len(chunks)<per_state:
            idx=max(range(len(chunks)),key=lambda j:len(chunks[j]))
            g=chunks.pop(idx);axis='lat' if g.lat.max()-g.lat.min()>(g.lon.max()-g.lon.min())*np.cos(np.radians(g.lat.mean())) else 'lon'
            g=g.sort_values([axis,'geohash']);cut=len(g)//2
            chunks.extend([g.iloc[:cut].copy(),g.iloc[cut:].copy()])
        for i,g in enumerate(sorted(chunks,key=lambda g:(g.supply_bus.iloc[0],g.lat.mean(),g.lon.mean()))):
            g['zone_id']=state.replace(' ','_')+f'_{i+1:02d}';groups.append(g)
    return pd.concat(groups,ignore_index=True)

def prepare():
    DATA.mkdir(parents=True,exist_ok=True)
    source=ROOT/'research/dre_atlas_2025/data/settlement_attributes.csv.gz'
    atlas=pd.read_csv(source);atlas=atlas[atlas.admin_cgaz_1.isin(CORE)].copy()
    assert len(atlas)==11268 and atlas.geohash.is_unique
    assert np.isfinite(atlas[['lat','lon','num_connections','hull_area','distance_to_existing_transmission_lines']]).all().all()
    assert (atlas.num_connections>0).all() and (atlas.hull_area>=0).all()
    n=pypsa.Network(ROOT/'data/national_coupling/national_reference.nc')
    sector=pd.read_csv(ROOT/'data/report_evidence/sector_sales_customers.csv')
    s=sector[(sector.data_period==2017)&(~sector.is_total)]
    residential=float(s.loc[s.sector.eq('Residential'),'sales_MWh'].sum()/s.sales_MWh.sum())
    weather=pd.read_csv(ROOT/'data/spatial_proxy_study/sites.csv').set_index('admin_cgaz_1')
    weights=json.loads((ROOT/'data/electrification_pilot/config.json').read_text())['hourly_demand_weights']
    wrows=[]
    for state in CORE:
        w=weather.loc[state];name=f'weather_{w.geohash}_2022.csv.gz'
        shutil.copy2(ROOT/'data/spatial_proxy_study'/name,DATA/name)
        wrows.append(dict(state=state,geohash=w.geohash,lat=w.lat,lon=w.lon,file=name,
                          maximum_cluster_distance_km=float(km(atlas.loc[atlas.admin_cgaz_1.eq(state),'lon'],atlas.loc[atlas.admin_cgaz_1.eq(state),'lat'],w.lon,w.lat).max())))
    pd.DataFrame(wrows).to_csv(DATA/'weather_proxies.csv',index=False,lineterminator='\n')
    for count in [6,8]:
        a=zones(atlas,n,count);rows=[]
        for zid,g in a.groupby('zone_id',sort=False):
            bus=g.supply_bus.iloc[0];all_at_bus=a[a.supply_bus.eq(bus)]
            baseline=n.loads_t.p_set[bus+' consumption'].sum()*residential*g.num_connections.sum()/all_at_bus.num_connections.sum()
            target=max(float(baseline),float(g.num_connections.sum()*365/1000))
            rows.append(dict(zone_id=zid,state=g.admin_cgaz_1.iloc[0],supply_bus=bus,
                clusters=len(g),connections=int(g.num_connections.sum()),lon=np.average(g.lon,weights=g.num_connections),lat=np.average(g.lat,weights=g.num_connections),
                baseline_residential_MWh=float(baseline),target_MWh=target,uplift_MWh=target-baseline,
                lv_km=float((1.3*np.sqrt(g.num_connections*g.hull_area)).sum()),
                mv_km=float((1.3*g.distance_to_existing_transmission_lines).sum()),
                transformer_units=float(np.maximum(1,np.ceil((g.num_connections/g.num_connections.sum()*target/365*max(weights)/sum(weights))/.9/.08)).sum())))
        table=pd.DataFrame(rows)
        table.to_csv(DATA/f'zones_{count*6}.csv',index=False,lineterminator='\n')
        a[['geohash','admin_cgaz_1','zone_id','supply_bus','num_connections','lat','lon']].to_csv(DATA/f'crosswalk_{count*6}.csv.gz',index=False,compression={'method':'gzip','mtime':0},lineterminator='\n')
    repair_ids=['merowe_khartoum','atbara_khartoum','khartoum_medani','khartoum_kosti']
    rows=[]
    for name,l in n.links.iterrows():
        length=float(km(n.buses.at[l.bus0,'x'],n.buses.at[l.bus0,'y'],n.buses.at[l.bus1,'x'],n.buses.at[l.bus1,'y'])*1.3)
        candidate=name in repair_ids
        rows.append(dict(asset_id=name,bus0=l.bus0,bus1=l.bus1,reference_MW=l.p_nom,
            available_fraction=.1 if candidate else 1.,candidate_repair=candidate,route_proxy_km=length,
            repair_initial_USD=(length*70000+2000000) if candidate else 0,
            evidence='Schematic 2022 corridor; 10% availability and repair cost are analyst scenarios, not surveyed damage' if candidate else 'Schematic 2022 reference; unchanged'))
    pd.DataFrame(rows).to_csv(DATA/'corridor_register.csv',index=False,lineterminator='\n')
    config=dict(states=CORE,reference_year=2022,base_zones=36,resolution_check_zones=48,
        residential_share=residential,residential_share_source='R19 Annex 3, 2017 sector shares, applied as an allocation assumption to 2022 regional totals',
        daily_service_floor_kWh_per_potential_connection=1.,existing_distribution_rehabilitation_fraction=.35,
        bulk_price_for_candidate_sizing_USD_MWh=140.,repair_life_years=20,repair_annual_om_fraction=.02,
        hv_repair_USD_per_proxy_km=70000.,terminal_repair_USD_per_corridor=2000000.,
        weather='One cached 2022 NASA POWER profile per state; explicit spatial proxy, not independent zone weather',
        hydro='2012 monthly generation shapes normalized to 2022 annual hydro limits; scenario seasonality, not 2022 measured inflows',
        scenarios={'restricted':dict(repair_budget_USD=0,outage_local_hours=[18,19,20,21,22,23],force_repairs=False),
                   'selective':dict(repair_budget_USD=45000000,outage_local_hours=[19,20,21],force_repairs=False),
                   'restored':dict(repair_budget_USD=1e12,outage_local_hours=[],force_repairs=True)},
        candidate_scope='Binary zone choice from independently sized fixed hourly portfolios; national dispatch and four corridor repairs jointly optimized. No unrestricted joint local capacity optimum.',
        mip_gap=.0005,time_limit_seconds=1800)
    (DATA/'config.json').write_text(json.dumps(config,indent=2)+'\n')
    sources=[source,ROOT/'data/report_evidence/sector_sales_customers.csv',ROOT/'research/forecasting_2012/data/hydro_monthly.csv',ROOT/'data/national_coupling/national_reference.nc',ROOT/'data/spatial_proxy_study/weather_manifest.json']
    (DATA/'sources.json').write_text(json.dumps({p.relative_to(ROOT).as_posix():sha(p) for p in sources},indent=2)+'\n')
    print('Prepared all',len(atlas),'clusters; 36 and 48 zones; residential share',residential)

if __name__=='__main__':prepare()
