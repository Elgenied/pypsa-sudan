"""Replay saved section-14 networks and reconstruct costs independently."""
import json,gc
import numpy as np
import pandas as pd
import model as m
from check_coupled import load_network,electrical_checks,TOL

def check_case(sc,free):
    folder=m.OUT/(sc+('_joint_choices' if free else '_fixed_choices'))
    s=json.loads((folder/'summary.json').read_text());manifest=json.loads((folder/'manifest.json').read_text())
    assert manifest['inputs']==m.fingerprint(sc,free)
    assert all(m.lib.r.sha(folder/f)==h for f,h in manifest['outputs'].items())
    zones,gez,previous,library,repairs,old,off,fixed,physical,unit=m.inputs(sc)
    n=load_network(folder/'network.nc');balance=electrical_checks(n)
    assert not n.generators.carrier.isin(['shortage','unserved_diagnostic']).any()
    choices=pd.read_csv(folder/'choices.csv').set_index('zone_id');assert set(choices.index)==set(gez.zone_id)
    reference=m.base.coupled.national_network(np.zeros(8760));reference.remove('Load','additional_access')
    for name in reference.loads.index:
        factor=1-m.base.CONFIG['residential_share'] if reference.loads.at[name,'bus'] in zones.supply_bus.unique() else 1
        assert np.max(abs(n.loads_t.p_set[name]-reference.loads_t.p_set[name]*factor))<TOL
    outside=previous[previous.state.ne('Gezira')]
    assert set(n.loads.index[n.loads.index.str.startswith('outside_')])==set('outside_'+z for z in outside.index[outside['mode'].eq('grid')])
    for zid,r in outside.iterrows():
        if r['mode']=='grid':
            h=pd.read_csv(m.lib.OUT/library.at[r.key,'hourly_file'])
            assert np.max(abs(n.loads_t.p_set['outside_'+zid]-h.grid_MW.to_numpy()*r.scale))<TOL
    register=pd.read_csv(m.base.DATA/'corridor_register.csv').set_index('asset_id')
    for name,r in register.iterrows():
        limit=r.reference_MW
        if r.candidate_repair:limit*=r.available_fraction+(1-r.available_fraction)*repairs.at[name,'selected']
        assert abs(n.links.at[name,'p_nom']-limit)<TOL
        assert n.links_t.p0[name].abs().max()<=limit+TOL
    for b in m.base.monthly_budgets(n).itertuples():assert n.generators_t.p.loc[n.snapshots.month==b.month,b.generator].sum()<=b.budget_MWh+.1
    for name,g in n.generators.query("carrier == 'hydro'").iterrows():assert n.generators_t.p[name].sum()<=g.e_sum_max+.1
    hourly=[];costs=[];max_soc=0.;cycling=0.
    for z in gez.itertuples():
        zid=z.zone_id;r=choices.loc[zid];grid=r['mode']=='grid';scale=z.target_MWh/365;h=physical[zid]
        prior=previous.loc[zid]
        if prior['mode']=='grid':
            assert prior.pv_kWp/1000<=5*scale+TOL
            assert prior.battery_nominal_kWh/1000<=30*scale+TOL
            assert prior.converter_AC_kW/1000<=5*scale+TOL
            ph=pd.read_csv(m.lib.OUT/library.at[prior.key,'hourly_file'])
            assert ph.grid_MW.max()*scale<=scale+TOL
            prior_cost=fixed[zid]+prior.pv_kWp*unit['pv']+prior.battery_nominal_kWh*unit['battery']+prior.converter_AC_kW*unit['converter']
            assert abs(prior_cost-prior.local_EAC_USD)<1,'Retained reference design costs changed'
        if not free:assert grid==(previous.at[zid,'mode']=='grid')
        pv=n.generators_t.p['pv_'+zid];imports=n.links_t.p0['import_'+zid];charge=n.links_t.p0['charge_'+zid];discharge=-n.links_t.p1['discharge_'+zid];energy=n.stores_t.e['store_'+zid]
        delivered=h.target_delivered_MW*scale
        assert np.max(abs(n.loads_t.p_set['service_'+zid]-delivered/.9))<TOL
        cancel=n.generators_t.p['cancel_'+zid];assert np.max(abs(cancel-(0 if grid else delivered/.9)))<TOL
        assert np.max(abs(pv+imports+discharge-charge-delivered/.9*int(grid)))<TOL
        residual=energy-np.roll(energy,1)-.95*charge+discharge/.95;max_soc=max(max_soc,float(residual.abs().max()));assert residual.abs().max()<TOL
        pv_cap=n.generators.at['pv_'+zid,'p_nom_opt'];battery=n.stores.at['store_'+zid,'e_nom_opt'];converter=n.links.at['charge_'+zid,'p_nom_opt']
        assert -.00001<=pv_cap<=5*scale*grid+TOL and -.00001<=battery<=30*scale*grid+TOL and -.00001<=converter<=5*scale*grid+TOL
        assert imports.min()>-TOL and imports.max()<=scale*grid+TOL
        assert np.max(pv-h.pv_available_pu.to_numpy()*pv_cap)<TOL
        assert np.max(charge+discharge-converter)<TOL
        assert abs(converter-.95*n.links.at['discharge_'+zid,'p_nom_opt'])<TOL
        assert energy.min()>=.1*battery-TOL and energy.max()<=.9*battery+TOL
        cycling+=float(np.minimum(charge.clip(lower=0),discharge.clip(lower=0)).sum())
        hours=m.base.CONFIG['scenarios'][sc]['outage_local_hours']
        if hours:assert imports.loc[((imports.index.hour+2)%24).isin(hours)].abs().max()<TOL
        if grid:
            # Rebuild the full lifecycle ledger through package(), rather than the sizing slope objective.
            cat=library.copy();key=m.lib.key_for(36,zid,'grid',sc)
            for col,v in [('pv_kWp',pv_cap*1000),('battery_nominal_kWh',battery*1000),('converter_AC_kW',converter*1000),('diesel_kW',0)]:cat.at[key,col]=v/scale
            cat.at[key,'diesel_generation_kWh']=0
            rec=m.lib.package(z,'grid',sc,cat.reset_index());cost=rec['local_EAC_USD']
            for col in ['pv_kWp','battery_nominal_kWh','converter_AC_kW']:assert abs(rec[col]-r[col])<.01
        else:
            rec=off.loc[zid];cost=rec.local_EAC_USD;assert r['mode']==rec['mode']
            oh=pd.read_csv(m.lib.OUT/library.at[rec.key,'hourly_file'])
            assert np.max(abs((oh.pv_MW+oh.diesel_MW+oh.discharge_MW-oh.charge_MW-oh.bus_load_MW)*scale))<TOL
            assert abs(oh.target_delivered_MW.sum()*scale-z.target_MWh)<.01
        assert abs(cost-r.local_annual_cost_USD)<1
        assert abs(imports.sum()-r.grid_import_MWh)<.01
        costs.append(cost)
        hourly.append(pd.DataFrame(dict(time_UTC=n.snapshots,zone_id=zid,grid_selected=grid,target_delivered_MW=delivered.to_numpy(),pv_MW=pv.to_numpy(),grid_MW=imports.to_numpy(),charge_MW=charge.to_numpy(),discharge_MW=discharge.to_numpy(),battery_MWh=energy.to_numpy())))
    assert cycling<.01,('Simultaneous cycling',cycling)
    national=float((n.generators_t.p.sum()*n.generators.marginal_cost).sum())
    cost=national+sum(costs)+outside.local_EAC_USD.sum()+old['annual_repair_cost_USD'];assert abs(cost-s['annual_system_cost_USD'])<1
    link_operating_penalty=float((n.links_t.p0.sum()*n.links.marginal_cost).sum())
    assert abs(link_operating_penalty-s['cycling_tiebreak_USD'])<.01
    assert s['annual_system_cost_USD']<=old['annual_system_cost_USD']+max(1,old['annual_system_cost_USD']*.0001)
    result=dict(case=folder.name,passed=True,hours=8760,gezira_zones=6,potential_connections=int(gez.connections.sum()),max_bus_balance_error_MW=balance,max_storage_balance_error_MWh=max_soc,simultaneous_charge_discharge_MWh=cycling,independent_ledger_reconstruction=True,field_validated=False)
    derived=m.OUT/'checked';derived.mkdir(exist_ok=True)
    pd.concat(hourly).to_csv(derived/(folder.name+'_hourly.csv.gz'),index=False,compression={'method':'gzip','mtime':0})
    (derived/(folder.name+'_validation.json')).write_text(json.dumps(result,indent=2));del n;gc.collect();return result

def check():
    from check_regional import library_checks
    library_checks()  # Recheck cached hourly candidates used by fixed outside and off-grid choices.
    rows=[check_case(sc,free) for sc in ['selective','restored'] for free in [False,True]]
    for sc in ['selective','restored']:
        a=json.loads((m.OUT/f'{sc}_fixed_choices/summary.json').read_text());b=json.loads((m.OUT/f'{sc}_joint_choices/summary.json').read_text())
        assert b['annual_system_cost_USD']<=a['annual_system_cost_USD']+a['annual_system_cost_USD']*.0001
    result=dict(passed=True,cases=rows,scope='Independent saved-output checks; no field validation');(m.OUT/'validation.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))

if __name__=='__main__':check()
