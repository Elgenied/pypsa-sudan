"""Reconstruct source-proxy demand, hourly feasibility and lifecycle economics."""
import hashlib,json
import numpy as np
import pandas as pd
import pilot_model as pilot
from spatial_proxy_model import DATA,OUT,DESIGN,PRICE,context,daily_demand,task_list,fingerprints,sha
from cost_model import annuity

def check():
    manifest=json.loads((OUT/'manifest.json').read_text())
    assert manifest['complete'] and manifest['inputs']==fingerprints()
    for name,digest in manifest['outputs'].items():assert sha(OUT/name)==digest,name
    source=json.loads((DATA/'selection_manifest.json').read_text())
    # Preparation records exact bytes; preserve its separate raw-file hashes.
    def rawsha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
    assert rawsha(DATA/'sites.csv')==source['selected_file_sha256']
    assert rawsha(DATA/'coverage.csv')==source['coverage_file_sha256']
    assert rawsha(DATA/'atlas_context_points.csv.gz')==source['context_points_sha256']
    sites=pd.read_csv(DATA/'sites.csv');assert len(sites)==18 and sites.admin_cgaz_1.nunique()==18 and sites.geohash.is_unique
    assert (sites.num_connections==sites.large_buildings+sites.medium_buildings+sites.small_buildings).all()
    assert (sites.demand-(1.1*sites.large_buildings+.65*sites.medium_buildings+.335*sites.small_buildings)).abs().max()<=.050001
    assert np.allclose(sites.atlas_daily_kWh_per_connection,sites.demand/sites.num_connections)
    assert sites.grid_in_local_scope.equals(sites.distance_to_existing_transmission_lines<=DESIGN['grid_max_straight_distance_km'])
    assert not sites.has_nightlight.any()
    weather=json.loads((DATA/'weather_manifest.json').read_text())
    assert len(weather['weather'])==18 and {x['geohash'] for x in weather['weather']}==set(sites.geohash)
    for w in weather['weather']:assert rawsha(DATA/w['file'])==w['file_sha256']
    atlas_path=pilot.ROOT/source['source_file'];selection_rechecked=False
    if atlas_path.exists():
        assert rawsha(atlas_path)==source['source_sha256']
        atlas=pd.read_csv(atlas_path);cfg=DESIGN['selection']
        good=np.isfinite(atlas[cfg['features']+['demand','building_density_percent']]).all(axis=1)
        good &= atlas.admin_cgaz_1.notna() & atlas.num_connections.between(cfg['minimum_connections'],cfg['maximum_connections'])
        good &= (atlas.hull_area>0)&atlas.building_density_percent.between(0,cfg['maximum_building_density_percent'])
        good &= (atlas.demand>0)&(atlas.pv_value>0)&(atlas.distance_to_existing_transmission_lines>=0)
        if cfg['require_no_detected_nightlight']:good &= ~atlas.has_nightlight
        eligible=atlas.loc[good]
        assert len(eligible)==source['eligible_clusters']
        for state,g in eligible.groupby('admin_cgaz_1'):
            features=g[cfg['features']].copy();features[cfg['log1p_features']]=np.log1p(features[cfg['log1p_features']])
            spread=(features.quantile(.75)-features.quantile(.25)).replace(0,1)
            score=(((features-features.median())/spread)**2).sum(axis=1)
            selected=g.assign(score=score).sort_values(['score','geohash']).iloc[0]
            saved=sites[sites.admin_cgaz_1==state].iloc[0]
            assert selected.geohash==saved.geohash
            for col in ['lat','lon','num_connections','demand','hull_area','pv_value','distance_to_existing_transmission_lines']:
                assert np.isclose(selected[col],saved[col]),col
        selection_rechecked=True
    summary=pd.read_csv(OUT/'summary.csv');tasks=task_list(list(sites.itertuples(index=False)))
    assert len(summary)==len(tasks)==manifest['unique_hourly_cases'] and summary.case_id.is_unique
    sites=sites.set_index('geohash');checks=[]
    for r in summary.itertuples(index=False):
        s=sites.loc[r.geohash].copy();s['geohash']=r.geohash
        assert r.mode!='grid_extension' or s.grid_in_local_scope
        h=pd.read_csv(OUT/'cases'/r.case_id/'hourly.csv.gz',parse_dates=['time_UTC']).set_index('time_UTC')
        with context(s,r.demand_case,r.outage_hours):
            cfg=pilot.CONFIG;_,cf,target=pilot.weather_and_load(s)
            assert len(h)==8760 and h.index.equals(target.index) and np.isfinite(h.to_numpy()).all()
            assert (h.target_delivered_MW-target).abs().max()<1e-9
            expected_annual=365*(s.demand if r.demand_case=='atlas_proxy' else s.num_connections*DESIGN['demand_cases'][r.demand_case]['daily_kWh_per_connection'])
            assert np.isclose(r.annual_delivered_kWh,expected_annual)
            assert np.isclose(r.daily_kWh_per_connection,daily_demand(s,r.demand_case))
            loss=0 if r.mode=='standalone' else cfg['mini_grid_distribution_loss' if r.mode=='mini_grid' else 'grid_distribution_loss']
            assert (h.bus_load_MW-target/(1-loss)).abs().max()<1e-9
            balance=h.pv_MW+h.diesel_MW+h.grid_MW+h.discharge_MW-h.charge_MW-h.bus_load_MW
            storage=h.battery_MWh-np.roll(h.battery_MWh,1)-(cfg['battery_charge_efficiency']*h.charge_MW-h.discharge_MW/cfg['battery_discharge_efficiency'])
            assert balance.abs().max()<1e-6 and storage.abs().max()<1e-6
            assert (h[['pv_MW','diesel_MW','grid_MW','charge_MW','discharge_MW']]>=-1e-7).all().all()
            assert (h.pv_MW<=r.pv_kWp/1000*cf+1e-6).all()
            assert (h.diesel_MW<=r.diesel_kW/1000+1e-6).all()
            assert (h.charge_MW+h.discharge_MW<=r.converter_AC_kW/1000+1e-6).all()
            assert (h.battery_MWh>=cfg['battery_min_soc']*r.battery_nominal_kWh/1000-1e-6).all()
            assert (h.battery_MWh<=cfg['battery_max_soc']*r.battery_nominal_kWh/1000+1e-6).all()
            assert np.minimum(h.charge_MW,h.discharge_MW).sum()<1e-4
            assert h.diesel_MW.sum()<=target.sum()*cfg['diesel_max_fraction_of_delivered_energy']+1e-6
            available=np.ones(len(h))
            if r.outage_hours:
                available[np.isin((h.index.hour+cfg['local_UTC_offset_hours'])%24,cfg['outage_local_hours'])]=0
            assert np.max(np.abs(h.grid_available_pu-available))<1e-9
            assert (h.grid_MW<=cfg['grid_tie_capacity_kW']/1000*available+1e-6).all()
            if r.mode!='grid_extension':assert h.grid_MW.abs().max()<1e-7
            if r.mode!='mini_grid':assert h.diesel_MW.abs().max()<1e-7
            caps={'pv_kWp':'pv_capacity_limit_kWp_per_service_point','battery_nominal_kWh':'battery_limit_kWh_per_service_point',
                  'converter_AC_kW':'converter_limit_kW_per_service_point','diesel_kW':'diesel_limit_kW_per_service_point'}
            assert all(getattr(r,k)<r.service_points*cfg[v]*.999 for k,v in caps.items())
            assert not r.design_bound_binding
            _,q,ledger,_,_,groups=pilot.cost_context(s,r.mode)
            capacities=dict(pv=r.pv_kWp,battery=r.battery_nominal_kWh,converter=r.converter_AC_kW,diesel=r.diesel_kW)
            for asset,parts in groups.items():
                for part in parts:q[part]=max(0,capacities[asset])
            costs=ledger(q);p=costs['parameters']
            annual=costs['summary']['equivalent_annual_cost_USD']-sum(costs['operating'][k] for k in ('grid_supply','diesel_fuel','diesel_runtime_maintenance'))
            annual+=h.grid_MW.sum()*1000*p['bulk_grid_supply']+h.diesel_MW.sum()*1000*(p['diesel_specific_fuel']*p['diesel_delivered_price']+p['diesel_variable_om'])
            assert abs(annual-r.equivalent_annual_cost_USD)<.05
            assert abs(annual/annuity(p['real_discount_rate'],p['horizon_years'])-r.lifecycle_NPC_USD)<.5
            assert abs(costs['summary']['initial_budget_USD']-r.initial_budget_USD)<.05
            assert np.isclose(annual/r.annual_delivered_kWh,getattr(r,PRICE))
            assert abs(r.annual_cost_objective_gap_USD)<.05
        checks.append(dict(case_id=r.case_id,hours=len(h),max_power_balance_error_MW=balance.abs().max(),
                           max_storage_balance_error_MWh=storage.abs().max(),annual_cost_reconstruction_gap_USD=annual-r.equivalent_annual_cost_USD))
    for (sid,demand),g in summary.groupby(['geohash','demand_case']):
        assert g.service_points.nunique()==1 and np.ptp(g.annual_delivered_kWh)<1e-6
        assert len(g)==(4 if sites.loc[sid,'grid_in_local_scope'] else 2)
        if sites.loc[sid,'grid_in_local_scope']:
            grid=g[g['mode']=='grid_extension'].sort_values('outage_hours')
            assert grid.iloc[1].equivalent_annual_cost_USD>=grid.iloc[0].equivalent_annual_cost_USD-.1
    for _,g in summary.groupby(['geohash','mode','outage_hours']):
        assert (g.sort_values('daily_kWh_per_connection').equivalent_annual_cost_USD.diff().dropna()>=-.1).all()
    pd.DataFrame(checks).to_csv(OUT/'independent_checks.csv',index=False,lineterminator='\n')
    report=dict(passed=True,selected_clusters=len(sites),states=18,unique_hourly_cases=len(summary),checked_case_hours=len(summary)*8760,
         grid_assessed_clusters=int(sites.grid_in_local_scope.sum()),grid_not_assessed_clusters=int((~sites.grid_in_local_scope).sum()),
         atlas_formula_reconstructed=True,full_atlas_selection_rechecked=selection_rechecked,equal_service=True,
         lifecycle_costs_reconstructed=True,measured_settlement_demand_used=False,national_extrapolation=False,field_validated=False)
    (OUT/'validation.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report));return report

if __name__=='__main__':check()
