"""Independent replay of the saved nested-candidate experiment."""
import json
import numpy as np
import pandas as pd
from check_coupled import load_network,electrical_checks,TOL
from check_regional import library_checks
import regional_candidate_diagnostic as d

def check():
    library,hourly=library_checks()
    cases=['restored_baseline_fixed','selective_expanded','restored_expanded','restored_expanded_gezira_grid']
    rows=[]
    for case in cases:
        folder=d.OUT/case;s=json.loads((folder/'summary.json').read_text());manifest=json.loads((folder/'manifest.json').read_text())
        assert manifest['inputs']==d.fingerprint(s['scenario'],s['expanded'],s['force_gezira'],s['fixed_choices'])
        assert all(d.lib.r.sha(folder/p)==h for p,h in manifest['outputs'].items())
        zones,_,options=d.candidates(s['scenario'],s['expanded']);chosen=pd.read_csv(folder/'zone_choices.csv')
        assert set(chosen.zone_id)==set(zones.zone_id) and chosen.zone_id.is_unique
        expected=options.set_index('key').loc[chosen.key].reset_index()
        for col in ['local_EAC_USD','initial_USD','target_MWh','connections','scale']:
            assert np.allclose(chosen[col],expected[col],atol=.01,rtol=1e-10),col
        assert np.isclose(chosen.target_MWh.sum(),zones.target_MWh.sum())
        n=load_network(folder/'network.nc');balance=electrical_checks(n)
        assert not n.generators.carrier.isin(['shortage','unserved_diagnostic']).any()
        reference=d.base.coupled.national_network(np.zeros(8760));reference.remove('Load','additional_access')
        for name in reference.loads.index:
            bus=reference.loads.at[name,'bus'];factor=1-d.base.CONFIG['residential_share'] if bus in zones.supply_bus.unique() else 1
            assert np.max(abs(n.loads_t.p_set[name]-reference.loads_t.p_set[name]*factor))<TOL
        for bus in zones.supply_bus.unique():
            delivered=np.zeros(8760)
            for row in chosen[chosen.supply_bus.eq(bus)].itertuples():
                h=hourly[row.key]
                assert np.max(abs(h.target_delivered_MW.to_numpy()*row.scale - hourly[row.key].target_delivered_MW.to_numpy()*row.target_MWh/365))<TOL
                if row.mode=='grid':
                    delivered+=h.grid_MW.to_numpy()*row.scale
                    hours=d.base.CONFIG['scenarios'][s['scenario']]['outage_local_hours']
                    if hours:assert h.loc[((h.index.hour+2)%24).isin(hours),'grid_MW'].abs().max()<TOL
            cancelled=n.generators_t.p.loc[:,n.generators.bus.eq(bus)&n.generators.carrier.eq('portfolio_accounting')].sum(axis=1)
            assert np.max(abs(n.loads_t.p_set['service_'+bus]-cancelled-delivered))<TOL
        repairs=pd.read_csv(folder/'repairs.csv').set_index('asset_id');inputs=pd.read_csv(d.base.DATA/'corridor_register.csv').set_index('asset_id')
        assert np.max(abs(repairs.selected-repairs.selected.round()))<1e-6
        for name,p in repairs.iterrows():
            e=inputs.loc[name];assert n.links_t.p0[name].abs().max()<=e.reference_MW*(e.available_fraction+(1-e.available_fraction)*p.selected)+TOL
        params={k:float(v['central']) for k,v in d.lib.inputs()[1].items()}
        factor=d.base.annuity(params['real_discount_rate'],d.base.CONFIG['repair_life_years'])+d.base.CONFIG['repair_annual_om_fraction']
        spend=float((repairs.selected*inputs.loc[repairs.index,'repair_initial_USD']).sum())
        assert spend<=d.base.CONFIG['scenarios'][s['scenario']]['repair_budget_USD']+.1
        if s['scenario']=='restored':assert (repairs.selected>.99999).all()
        for b in d.base.monthly_budgets(n).itertuples():assert n.generators_t.p.loc[n.snapshots.month==b.month,b.generator].sum()<=b.budget_MWh+.1
        for name,g in n.generators.query("carrier == 'hydro'").iterrows():
            assert n.generators_t.p[name].sum()<=g.e_sum_max+.1
        national=float((n.generators_t.p.sum()*n.generators.marginal_cost).sum())
        assert abs(national+expected.local_EAC_USD.sum()+spend*factor-s['annual_system_cost_USD'])<1
        if s['expanded']:
            original=pd.read_csv(d.base.OUT/f"{s['scenario']}_mixed_36_d1_f1/options.csv")
            assert set(original.key)<=set(options.key),'Not a nested feasible candidate set'
            retained=options.set_index('key').loc[original.key]
            for col in ['local_EAC_USD','initial_USD','target_MWh','scale','grid_import_MWh','pv_kWp','battery_nominal_kWh']:
                assert np.allclose(original[col],retained[col],atol=.01,rtol=1e-10),'Changed baseline candidate '+col
        if s['force_gezira']:assert chosen.loc[chosen.state.eq('Gezira'),'mode'].eq('grid').all()
        rows.append(dict(case=case,hours=len(n.snapshots),candidates=len(options),max_bus_balance_error_MW=balance,cost_reconstructed=True,passed=True))
    result=dict(passed=True,cases=rows,local_library_designs_checked=len(library),field_validated=False,claim='Nested finite-library robustness experiment; no unrestricted joint sizing or route optimization')
    (d.OUT/'validation.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2));return result

if __name__=='__main__':check()
