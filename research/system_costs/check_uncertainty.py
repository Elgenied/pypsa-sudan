"""Independent reconstruction of every uncertainty case and comparison table."""
import json
import numpy as np
import pandas as pd
import pilot_model as pilot
from uncertainty_model import OUT, DESIGN, PRICE, MODES, BASE_CONFIG, context, effective, fingerprints, sha
from cost_model import annuity

def check():
    manifest=json.loads((OUT/'manifest.json').read_text())
    assert manifest['complete'] and manifest['inputs']==fingerprints()
    for path,digest in manifest['outputs'].items():
        assert sha(OUT/path)==digest,f'Output hash mismatch: {path}'
    sites=pd.read_csv(pilot.DATA/'sites.csv').set_index('geohash')
    rows=pd.read_csv(OUT/'optimized_cases.csv');audit=[];records={}
    for r in rows.itertuples(index=False):
        changes=json.loads(r.assumptions_json)
        site=sites.loc[r.geohash].copy();site['geohash']=r.geohash
        h=pd.read_csv(OUT/'cases'/r.case_id/'hourly.csv.gz',parse_dates=['time_UTC']).set_index('time_UTC')
        with context(changes):
            cfg=pilot.CONFIG
            _,cf,target=pilot.weather_and_load(site)
            assert len(h)==8760 and h.index.equals(target.index) and np.isfinite(h.to_numpy()).all()
            assert (h.target_delivered_MW-target).abs().max()<1e-9
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
            availability=np.ones(len(h))
            if changes.get('outage_hours',0):
                availability[np.isin((h.index.hour+cfg['local_UTC_offset_hours'])%24,cfg['outage_local_hours'])]=0
            assert np.max(np.abs(h.grid_available_pu-availability))<1e-9
            assert (h.grid_MW<=cfg['grid_tie_capacity_kW']/1000*availability+1e-6).all()
            if r.mode!='grid_extension':assert h.grid_MW.abs().max()<1e-7
            if r.mode!='mini_grid':assert h.diesel_MW.abs().max()<1e-7
            assert not r.design_bound_binding
            inputs,q,ledger,_,_,groups=pilot.cost_context(site,r.mode)
            capacities={'pv':r.pv_kWp,'battery':r.battery_nominal_kWh,'converter':r.converter_AC_kW,'diesel':r.diesel_kW}
            for asset,parts in groups.items():
                for part in parts:q[part]=max(0,capacities[asset])
            costs=ledger(q);p=costs['parameters']
            fixed=costs['summary']['equivalent_annual_cost_USD']-sum(costs['operating'][k] for k in ('grid_supply','diesel_fuel','diesel_runtime_maintenance'))
            annual=fixed+h.grid_MW.sum()*1000*p['bulk_grid_supply']+h.diesel_MW.sum()*1000*(p['diesel_specific_fuel']*p['diesel_delivered_price']+p['diesel_variable_om'])
            assert abs(annual-r.equivalent_annual_cost_USD)<.05
            assert abs(annual/annuity(p['real_discount_rate'],p['horizon_years'])-r.lifecycle_NPC_USD)<.5
            assert abs(costs['summary']['initial_budget_USD']-r.initial_budget_USD)<.05
            assert abs(r.annual_cost_objective_gap_USD)<.05
            assert np.isclose(target.sum()*1000,r.annual_delivered_kWh)
            assert np.isclose(annual/r.annual_delivered_kWh,getattr(r,PRICE))
        records[r.case_id]=r
        audit.append(dict(case_id=r.case_id,hours=len(h),max_balance_error_MW=balance.abs().max(),
                          max_SOC_error_MWh=storage.abs().max(),annual_cost_gap_USD=annual-r.equivalent_annual_cost_USD))
    oat=pd.read_csv(OUT/'one_at_a_time.csv');joint=pd.read_csv(OUT/'joint_scenarios.csv')
    assert len(oat)==sum(len(v['values']) for v in DESIGN['axes'].values())*len(sites)*3
    assert len(joint)==8*len(sites)*3
    for table,group in [(oat,['geohash','axis','value']),(joint,['geohash','joint_scenario'])]:
        for _,g in table.groupby(group):
            assert set(g['mode'])==set(MODES) and len(g)==3
            assert np.ptp(g.annual_delivered_kWh)<1e-6
        for r in table.itertuples(index=False):
            cached=records[r.case_id]
            assert effective(r.mode,json.loads(r.scenario_assumptions_json))==effective(r.mode,
                 {**json.loads(cached.assumptions_json),**({r.axis:r.value} if hasattr(r,'axis') else {})})
            site=sites.loc[r.geohash].copy();site['geohash']=r.geohash
            with context(effective(r.mode,json.loads(r.scenario_assumptions_json))):
                _,q,ledger,_,_,groups=pilot.cost_context(site,r.mode)
                capacities={'pv':r.pv_kWp,'battery':r.battery_nominal_kWh,'converter':r.converter_AC_kW,'diesel':r.diesel_kW}
                for asset,parts in groups.items():
                    for part in parts:q[part]=max(0,capacities[asset])
                costs=ledger(q);p=costs['parameters']
                annual=costs['summary']['equivalent_annual_cost_USD']-sum(costs['operating'][k] for k in ('grid_supply','diesel_fuel','diesel_runtime_maintenance'))
                annual+=r.grid_import_kWh*p['bulk_grid_supply']+r.diesel_generation_kWh*(p['diesel_specific_fuel']*p['diesel_delivered_price']+p['diesel_variable_om'])
                assert abs(annual-r.equivalent_annual_cost_USD)<.05
                assert abs(costs['summary']['initial_budget_USD']-r.initial_budget_USD)<.05
                assert np.isclose(annual/r.annual_delivered_kWh,getattr(r,PRICE))
    # Nested outages and higher purchase prices cannot lower minimized annual cost.
    for axis in ('outage_hours','pv_cost_factor','battery_cost_factor','diesel_price','grid_price','standalone_markup','mv_cost_factor','lv_length_factor','daily_kWh'):
        for _,g in oat[oat.axis==axis].groupby(['geohash','mode']):
            assert (g.sort_values('value').equivalent_annual_cost_USD.diff().dropna()>=-.1).all(),axis
    rt=pd.read_csv(OUT/'route_thresholds.csv')
    for r in rt.itertuples(index=False):
        assert r.MV_annual_USD_per_route_km>0
        if r.status=='nonnegative_crossing':
            assert abs(r.grid_zero_route_annual_USD+r.MV_annual_USD_per_route_km*r.break_even_new_MV_route_km-r.offgrid_annual_USD)<.01
        else:assert r.grid_zero_route_annual_USD>r.offgrid_annual_USD
    dt=pd.read_csv(OUT/'demand_thresholds.csv')
    for r in dt.query("status=='sign_change_bracket'").itertuples(index=False):
        assert r.upper_kWh_day-r.lower_kWh_day<=DESIGN['demand_break_even_tolerance_kWh_day']+1e-12
        assert r.lower_mini_minus_standalone_USD_kWh*r.upper_mini_minus_standalone_USD_kWh<=0
    pd.DataFrame(audit).to_csv(OUT/'independent_checks.csv',index=False,lineterminator='\n')
    report=dict(passed=True,unique_hourly_cases=len(rows),fresh_solves=int((~rows.baseline_reused).sum()),
        checked_case_hours=len(rows)*8760,one_at_a_time_comparisons=len(oat),joint_option_comparisons=len(joint),
        equal_service=True,lifecycle_costs_reconstructed=True,scenario_probabilities_assigned=False,
        field_validated=False,any_artificial_design_bound_binding=False)
    (OUT/'validation.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report));return report

if __name__=='__main__':check()
