"""Recompute feasibility and cost checks from saved hourly outputs, without solving."""
import hashlib,json
import numpy as np
import pandas as pd
from pilot_model import DATA,OUT,CONFIG,fingerprint,weather_and_load,cost_context
from cost_model import annuity


def check():
    manifest=json.loads((OUT/'run_manifest.json').read_text())
    assert manifest['complete'] and manifest['runs']==18
    assert manifest['inputs']==fingerprint(),'Inputs/code changed: rerun the pilot'
    for name,digest in manifest['output_hashes'].items():
        assert hashlib.sha256((OUT/name).read_bytes()).hexdigest()==digest,f'Changed output: {name}'
    provenance=json.loads((DATA/'source_manifest.json').read_text())
    for source in provenance['weather']:
        assert hashlib.sha256((DATA/source['file']).read_bytes()).hexdigest()==source['file_sha256']
    sites=pd.read_csv(DATA/'sites.csv').set_index('geohash')
    summary=pd.read_csv(OUT/'summary.csv')
    assert len(summary)==18 and summary.run_id.nunique()==18
    checks=[]
    for r in summary.itertuples(index=False):
        site=sites.loc[r.geohash].copy();site['geohash']=r.geohash
        h=pd.read_csv(OUT/f'{r.run_id}_hourly.csv.gz',parse_dates=['time_UTC']).set_index('time_UTC')
        w,cf,target=weather_and_load(site,r.demand_multiplier)
        assert len(h)==8760 and h.index.equals(target.index) and h.notna().all().all()
        assert np.max(np.abs(h.target_delivered_MW-target))<1e-9
        balance=h.pv_MW+h.grid_MW+h.diesel_MW+h.discharge_MW-h.charge_MW-h.bus_load_MW
        storage=h.battery_MWh-np.roll(h.battery_MWh,1)-(CONFIG['battery_charge_efficiency']*h.charge_MW-h.discharge_MW/CONFIG['battery_discharge_efficiency'])
        assert balance.abs().max()<1e-6 and storage.abs().max()<1e-6
        assert (h.pv_MW<=r.pv_kWp/1000*cf+1e-6).all()
        assert (h.diesel_MW<=r.diesel_kW/1000+1e-6).all()
        assert (h.grid_MW<=CONFIG['grid_tie_capacity_kW']/1000*h.grid_available_pu+1e-6).all()
        assert (h[['pv_MW','diesel_MW','grid_MW','charge_MW','discharge_MW']]>=-1e-6).all().all()
        assert (h.charge_MW+h.discharge_MW<=r.converter_AC_kW/1000+1e-6).all()
        assert (h.battery_MWh>=CONFIG['battery_min_soc']*r.battery_nominal_kWh/1000-1e-6).all()
        assert (h.battery_MWh<=CONFIG['battery_max_soc']*r.battery_nominal_kWh/1000+1e-6).all()
        assert h.diesel_MW.sum()<=h.target_delivered_MW.sum()*CONFIG['diesel_max_fraction_of_delivered_energy']+1e-6
        if r.scenario=='no_diesel' or r.mode!='mini_grid':
            assert h.diesel_MW.abs().max()<1e-7
        if r.mode!='grid_extension':
            assert h.grid_MW.abs().max()<1e-7
        elif r.scenario=='evening_outage':
            outage=((h.index.hour+CONFIG['local_UTC_offset_hours'])%24).isin(CONFIG['outage_local_hours'])
            assert h.loc[outage,'grid_MW'].abs().max()<1e-7
        assert np.minimum(h.charge_MW,h.discharge_MW).sum()<1e-4
        assert np.isclose(h.target_delivered_MW.sum()*1000,r.annual_delivered_kWh)
        assert np.isclose(r.equivalent_annual_cost_USD/r.annual_delivered_kWh,r.modelled_LCOE_USD_per_kWh)
        # Recompute complete cost from optimized quantities and saved dispatch.
        inputs,q,ledger,intercept,units,groups=cost_context(site,r.mode,r.demand_multiplier)
        capacities=dict(pv=r.pv_kWp,battery=r.battery_nominal_kWh,converter=r.converter_AC_kW,diesel=r.diesel_kW)
        for asset,parts in groups.items():
            for component in parts:q[component]=max(0,capacities[asset])
        costs=ledger(q)
        p=costs['parameters']
        fixed=costs['summary']['equivalent_annual_cost_USD']-sum(costs['operating'][k] for k in ('grid_supply','diesel_fuel','diesel_runtime_maintenance'))
        annual=fixed+h.grid_MW.sum()*1000*p['bulk_grid_supply']+h.diesel_MW.sum()*1000*(p['diesel_specific_fuel']*p['diesel_delivered_price']+p['diesel_variable_om'])
        assert abs(annual-r.equivalent_annual_cost_USD)<.05
        assert abs(r.annual_cost_objective_gap_USD)<.05
        # The mathematical standalone dispatch can be allocated identically to each home.
        if r.mode=='standalone':assert (balance/r.service_points).abs().max()<1e-6
        checks.append(dict(run_id=r.run_id,hours_checked=len(h),max_balance_error_MW=balance.abs().max(),
                           max_storage_error_MWh=storage.abs().max(),annual_cost_reconstruction_gap_USD=annual-r.equivalent_annual_cost_USD))
    # All base architectures receive exactly the same service-point count and annual load per site.
    base=summary.query("scenario=='base'")
    for _,group in base.groupby('geohash'):
        assert len(group)==3 and group.service_points.nunique()==1
        assert np.ptp(group.annual_delivered_kWh)<1e-5
    # Removing a fuel option or restricting grid availability cannot improve optimum cost.
    for r in summary.query("scenario in ['no_diesel','evening_outage']").itertuples(index=False):
        ref=base[(base.geohash==r.geohash)&(base['mode']==r.mode)].iloc[0]
        assert r.equivalent_annual_cost_USD>=ref.equivalent_annual_cost_USD-.1
    pd.DataFrame(checks).to_csv(OUT/'independent_checks.csv',index=False,lineterminator='\n')
    report=dict(passed=True,optimized_cases=18,hourly_case_snapshots=18*8760,
                same_service=True,source_hashes=True,lifecycle_objective_reconciled=True,
                status='Numerical and data integrity checks only; no independent field validation')
    report['any_design_bound_binding']=bool(
        (summary.pv_kWp>=summary.service_points*CONFIG['pv_capacity_limit_kWp_per_service_point']*.999).any()
        or (summary.battery_nominal_kWh>=summary.service_points*CONFIG['battery_limit_kWh_per_service_point']*.999).any()
        or (summary.converter_AC_kW>=summary.service_points*CONFIG['converter_limit_kW_per_service_point']*.999).any()
        or (summary.diesel_kW>=summary.service_points*CONFIG['diesel_limit_kW_per_service_point']*.999).any())
    (OUT/'validation.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report))
    return report


if __name__=='__main__':check()
