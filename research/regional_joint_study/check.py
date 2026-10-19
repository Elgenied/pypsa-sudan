"""Independent physical, coverage and cost checks of investment and replay outputs."""
import argparse
import gc
import json
import numpy as np
import pandas as pd
import model as m
from check_coupled import load_network, electrical_checks, TOL


def cap(table, name, nominal='p_nom'):
    return float(table.at[name, nominal+'_opt'] if table.at[name, nominal+'_extendable'] else table.at[name, nominal])


def check_case(c, include_replay=True):
    folder = m.OUT/c.key
    assert m.valid(folder, m.fingerprint(c)), 'Input/output fingerprints changed'
    assert m.lib.valid(m.lib.OUT), 'Inherited local-library integrity'
    checked=folder/'checked';checked.mkdir(exist_ok=True)
    check_fp=dict(checker=m.lib.r.sha(m.HERE/'check.py'), investment=m.lib.r.sha(folder/'manifest.json'),
                  replay=m.lib.r.sha(folder/'replay/manifest.json') if include_replay else None)
    if m.valid(checked,check_fp):
        return json.loads((checked/'validation.json').read_text())
    s = json.loads((folder/'summary.json').read_text())
    zones, library, profiles, alternatives, off, fixed, _, unit = m.inputs(c)
    choices = pd.read_csv(folder/'choices.csv').set_index('zone_id')
    repairs = pd.read_csv(folder/'repairs.csv').set_index('asset_id')
    assert choices.index.is_unique and set(choices.index)==set(zones.zone_id)
    cross = pd.read_csv(m.base.DATA/f'crosswalk_{c.zones}.csv.gz')
    source = pd.read_csv(m.ROOT/'research/dre_atlas_2025/data/settlement_attributes.csv.gz')
    source = source[source.admin_cgaz_1.isin(m.base.CONFIG['states'])]
    assert cross.geohash.is_unique and set(cross.geohash)==set(source.geohash)
    assert len(cross)==11268 and int(cross.num_connections.sum())==10078666
    assert set(zones.state)==set(m.base.CONFIG['states'])
    grouped = cross.groupby('zone_id').agg(connections=('num_connections','sum'), clusters=('geohash','size'))
    assert np.max(abs(grouped-zones.set_index('zone_id')[['connections','clusters']]).to_numpy())<.01
    assert np.max(abs(choices.target_MWh-zones.set_index('zone_id').target_MWh*c.demand))<.01
    for relative, digest in json.loads((m.base.DATA/'sources.json').read_text()).items():
        assert m.lib.r.sha(m.ROOT/relative)==digest, relative
    assert s['mip_gap']<=.0001001
    assert np.max(abs(repairs.selected-repairs.selected.round()))<1e-6
    assert repairs.selected.between(0,1).all()
    sc = m.base.CONFIG['scenarios'][c.scenario]
    assert repairs.spend_USD.sum()<=sc['repair_budget_USD']+.01
    if sc['force_repairs']:
        assert repairs.selected.eq(1).all()
    if c.policy!='mixed':
        assert choices['mode'].eq('grid').all() if c.policy=='grid_led' else choices['mode'].ne('grid').all()
    reference = m.base.coupled.national_network(np.zeros(8760))
    reference.remove('Load','additional_access')
    register = pd.read_csv(m.base.DATA/'corridor_register.csv').set_index('asset_id')
    phases = ['investment','replay'] if include_replay else ['investment']
    metrics, annual_rows, hourly_rows = [], [], []
    for phase in phases:
        location = folder if phase=='investment' else folder/'replay'
        if phase=='replay':
            fp = dict(investment_manifest=m.lib.r.sha(folder/'manifest.json'), model=m.lib.r.sha(m.HERE/'model.py'))
            assert m.valid(location,fp)
        n = load_network(location/'network.nc')
        assert not n.generators.carrier.isin(['shortage','unserved_diagnostic']).any()
        balance = electrical_checks(n)
        for name in reference.loads.index:
            f = 1-m.base.CONFIG['residential_share'] if reference.loads.at[name,'bus'] in zones.supply_bus.unique() else 1
            assert np.max(abs(n.loads_t.p_set[name]-reference.loads_t.p_set[name]*f))<TOL
        for name, row in reference.generators.iterrows():
            expected = row.marginal_cost*(c.fuel if row.carrier=='combustible' else 1)
            assert abs(n.generators.at[name,'marginal_cost']-expected)<1e-6
            assert abs(n.generators.at[name,'p_nom']-row.p_nom)<TOL
        for name, row in register.iterrows():
            limit = row.reference_MW
            if row.candidate_repair:
                limit *= row.available_fraction+(1-row.available_fraction)*repairs.at[name,'selected']
            assert n.links_t.p0[name].abs().max()<=limit+TOL
        for b in m.base.monthly_budgets(reference).itertuples():
            assert n.generators_t.p.loc[n.snapshots.month==b.month,b.generator].sum()<=b.budget_MWh+.1
        for name, row in reference.generators.query("carrier=='hydro'").iterrows():
            assert n.generators_t.p[name].sum()<=row.e_sum_max+.1
        soc_error, cycling, local_cost, initial = 0., 0., 0., 0.
        for z in zones.itertuples():
            zid, scale = z.zone_id, z.target_MWh*c.demand/365
            row = choices.loc[zid]
            grid = row['mode']=='grid'
            h = profiles[zid]
            target = h.target_delivered_MW.to_numpy()*scale
            weather=pd.read_csv(m.base.DATA/z.weather_file)
            ghi=weather.ALLSKY_SFC_SW_DWN.clip(lower=0)
            cf=(ghi/1000*.9*.96*(1-.004*(weather.T2M+25*ghi/800-25))).clip(0,1)
            assert np.max(abs(h.pv_available_pu.to_numpy()-cf.to_numpy()))<1e-8
            weights=np.asarray(m.lib.r.BASE['hourly_demand_weights'],float)
            expected=weights[(n.snapshots.hour+2)%24]/weights.sum()*scale
            assert np.max(abs(target-expected))<TOL
            pv = n.generators_t.p['pv_'+zid]
            imports = n.links_t.p0['import_'+zid]
            charge = n.links_t.p0['charge_'+zid]
            discharge = -n.links_t.p1['discharge_'+zid]
            energy = n.stores_t.e['store_'+zid]
            assert np.max(abs(n.loads_t.p_set['service_'+zid]-target/.9))<TOL
            assert np.max(abs(n.generators_t.p['cancel_'+zid]-(0 if grid else target/.9)))<TOL
            assert np.max(abs(pv+imports+discharge-charge-target/.9*grid))<TOL
            residual = energy-np.roll(energy,1)-.95*charge+discharge/.95
            soc_error = max(soc_error,float(residual.abs().max()))
            assert residual.abs().max()<TOL
            pv_cap = cap(n.generators,'pv_'+zid)
            battery = cap(n.stores,'store_'+zid,'e_nom')
            converter = cap(n.links,'charge_'+zid)
            assert -.00001<=pv_cap<=5*scale*grid+TOL
            assert -.00001<=battery<=30*scale*grid+TOL
            assert -.00001<=converter<=5*scale*grid+TOL
            assert np.max(pv-h.pv_available_pu.to_numpy()*pv_cap)<TOL
            assert np.max(charge+discharge-converter)<TOL
            assert abs(converter-.95*cap(n.links,'discharge_'+zid))<TOL
            assert energy.min()>=.1*battery-TOL and energy.max()<=.9*battery+TOL
            assert imports.min()>-TOL and imports.max()<=scale*grid+TOL
            if sc['outage_local_hours']:
                mask = ((n.snapshots.hour+2)%24).isin(sc['outage_local_hours'])
                assert imports.loc[mask].abs().max()<TOL
            cycling += float(np.minimum(charge.clip(lower=0),discharge.clip(lower=0)).sum())
            if grid:
                # Full lifecycle ledger from physical installed capacities; not objective coefficients.
                normalized = library.copy()
                key = m.lib.key_for(c.zones,zid,'grid',c.scenario)
                for col,v in [('pv_kWp',pv_cap*1000),('battery_nominal_kWh',battery*1000),('converter_AC_kW',converter*1000),('diesel_kW',0)]:
                    normalized.at[key,col]=v/scale
                    assert abs(row[col]-v)<.02
                normalized.at[key,'diesel_generation_kWh']=0
                reconstructed=m.lib.package(z,'grid',c.scenario,normalized.reset_index(),c.demand,c.fuel)
                real = pd.DataFrame(dict(time_UTC=n.snapshots,target_delivered_MW=target,pv_MW=pv.to_numpy(),grid_MW=imports.to_numpy(),diesel_MW=0.,charge_MW=charge.to_numpy(),discharge_MW=discharge.to_numpy(),battery_MWh=energy.to_numpy()))
            else:
                reconstructed = off.loc[zid]
                assert row['mode']==reconstructed['mode']
                oh = pd.read_csv(m.ROOT/row.profile_path,index_col=0,parse_dates=True)
                assert oh.index.equals(n.snapshots)
                assert np.max(abs(oh.target_delivered_MW.to_numpy()*scale-target))<TOL
                assert np.max(abs((oh.pv_MW+oh.diesel_MW+oh.discharge_MW-oh.charge_MW-oh.bus_load_MW)*scale))<TOL
                assert np.max(abs((oh.battery_MWh-np.roll(oh.battery_MWh,1)-.95*oh.charge_MW+oh.discharge_MW/.95)*scale))<TOL
                loss=0 if row['mode']=='standalone' else .08
                assert np.max(abs(oh.bus_load_MW-oh.target_delivered_MW/(1-loss)))<TOL
                assert np.max(oh.pv_MW.to_numpy()*scale-h.pv_available_pu.to_numpy()*row.pv_kWp/1000)<TOL
                assert np.max((oh.charge_MW+oh.discharge_MW)*scale-row.converter_AC_kW/1000)<TOL
                assert oh.battery_MWh.min()*scale>=.1*row.battery_nominal_kWh/1000-TOL
                assert oh.battery_MWh.max()*scale<=.9*row.battery_nominal_kWh/1000+TOL
                assert oh.diesel_MW.max()*scale<=row.diesel_kW/1000+TOL
                assert oh.diesel_MW.sum()<=.2*365+TOL and oh.grid_MW.abs().max()<TOL
                if row['mode']=='standalone':assert oh.diesel_MW.abs().max()<TOL
                assert oh[['pv_MW','diesel_MW','charge_MW','discharge_MW','battery_MWh']].min().min()>-TOL
                cycling += float(np.minimum(oh.charge_MW.clip(lower=0),oh.discharge_MW.clip(lower=0)).sum()*scale)
                real=oh[['target_delivered_MW','pv_MW','grid_MW','diesel_MW','charge_MW','discharge_MW','battery_MWh']].mul(scale).reset_index()
            assert abs(reconstructed['local_EAC_USD']-row.local_EAC_USD)<1
            assert abs(reconstructed['initial_USD']-row.initial_USD)<1
            local_cost+=reconstructed['local_EAC_USD'];initial+=reconstructed['initial_USD']
            if phase=='investment':
                real['state']=z.state;real['zone_id']=zid
                hourly_rows.append(real)
                annual_rows.append(dict(zone_id=zid,state=z.state,mode=row['mode'],**{k.replace('_MW','_MWh'):float(real[k].sum()) for k in ['target_delivered_MW','pv_MW','grid_MW','diesel_MW','charge_MW','discharge_MW']}))
        assert cycling<.1, ('Simultaneous cycling',cycling)
        national=float((n.generators_t.p.sum()*n.generators.marginal_cost).sum())
        params={k:float(v['central']) for k,v in m.lib.inputs()[1].items()}
        factor=m.annuity(params['real_discount_rate'],m.base.CONFIG['repair_life_years'])+m.base.CONFIG['repair_annual_om_fraction']
        repair_eac=float(repairs.spend_USD.sum()*factor)
        if phase=='investment':
            assert abs(local_cost+national+repair_eac-s['annual_system_cost_USD'])<2
            assert abs(initial+repairs.spend_USD.sum()-s['initial_local_and_repair_USD'])<2
            assert abs(national-s['national_operating_cost_USD'])<1
            generation=n.generators_t.p.sum().groupby(n.generators.carrier).sum()
            generation.drop(labels=['portfolio_accounting'],errors='ignore').rename('MWh').to_csv(checked/'national_generation.csv')
        else:
            assert not n.generators.p_nom_extendable.any() and not n.links.p_nom_extendable.any() and not n.stores.e_nom_extendable.any()
        metrics.append(dict(phase=phase,hours=8760,unserved_MWh=0.,max_bus_balance_error_MW=balance,max_storage_balance_error_MWh=soc_error,simultaneous_charge_discharge_MWh=cycling,passed=True))
        del n
        gc.collect()
    pd.DataFrame(annual_rows).to_csv(checked/'zone_energy.csv',index=False)
    hourly=pd.concat(hourly_rows,ignore_index=True).groupby(['state','time_UTC']).sum(numeric_only=True).reset_index()
    hourly.to_csv(checked/'state_hourly.csv.gz',index=False,compression={'method':'gzip','mtime':0})
    result=dict(case=c.key,passed=True,source_clusters=len(cross),potential_connections=int(cross.num_connections.sum()),phases=metrics,field_validated=False)
    (checked/'validation.json').write_text(json.dumps(result,indent=2))
    m.stamp(checked,check_fp,['zone_energy.csv','state_hourly.csv.gz','national_generation.csv','validation.json'])
    print(json.dumps(result),flush=True)
    return result


def check_all():
    results=[check_case(c) for c in m.cases()]
    for scenario in ['restricted','selective','restored']:
        summaries={p:json.loads((m.OUT/m.Case(scenario,p).key/'summary.json').read_text()) for p in ['mixed','grid_led','decentralized']}
        for policy in ['grid_led','decentralized']:
            assert summaries['mixed']['annual_system_cost_USD']<=summaries[policy]['annual_system_cost_USD']+summaries['mixed']['annual_system_cost_USD']*.00011
    a=m.lib.zones(36).groupby('supply_bus')[['connections','target_MWh','baseline_residential_MWh']].sum()
    b=m.lib.zones(48).groupby('supply_bus')[['connections','target_MWh','baseline_residential_MWh']].sum()
    assert np.max(abs(a-b).to_numpy())<.01
    (m.OUT/'validation.json').write_text(json.dumps(dict(passed=True,cases=results),indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--case');p.add_argument('--investment-only',action='store_true');a=p.parse_args()
    check_case(next(c for c in m.cases() if c.key==a.case),not a.investment_only) if a.case else check_all()
