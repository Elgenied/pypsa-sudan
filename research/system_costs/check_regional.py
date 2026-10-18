"""Check saved regional portfolios, every hourly national balance and cost accounting."""
import json
import numpy as np
import pandas as pd
import pypsa
import regional_model as m
from check_coupled import load_network,electrical_checks,require,TOL

def library_checks():
    lib=m.lib;require(lib.valid(lib.OUT),'Library hashes')
    table=pd.read_csv(lib.OUT/'summary.csv');records={}
    for r in table.itertuples():
        h=pd.read_csv(lib.OUT/r.hourly_file,index_col=0,parse_dates=True)
        require(len(h)==8760 and h.index.equals(pd.date_range('2022-01-01',periods=8760,freq='h')),'Library chronology')
        require(abs(h.target_delivered_MW.sum()-365)<1e-6,'Normalized portfolio service')
        weights=np.asarray(lib.r.BASE['hourly_demand_weights'],float)
        expected=weights[(h.index.hour+lib.r.BASE['local_UTC_offset_hours'])%24]/weights.sum()
        require(np.max(abs(h.target_delivered_MW-expected))<1e-10,'Identical prescribed hourly delivered service')
        require(np.max(abs(h.pv_MW+h.diesel_MW+h.grid_MW+h.discharge_MW-h.charge_MW-h.bus_load_MW))<TOL,'Local power balance')
        require(np.max(abs(h.battery_MWh-np.roll(h.battery_MWh,1)-.95*h.charge_MW+h.discharge_MW/.95))<TOL,'Cyclic storage')
        require(h[['pv_MW','diesel_MW','grid_MW','charge_MW','discharge_MW','battery_MWh']].min().min()>-TOL,'Nonnegative operation')
        w=pd.read_csv(lib.DATA/f'weather_{r.geohash}_2022.csv.gz');ghi=w.ALLSKY_SFC_SW_DWN.clip(lower=0)
        cf=(ghi/1000*.9*.96*(1-.004*(w.T2M+25*ghi/800-25))).clip(0,1)
        require(np.max(h.pv_MW.to_numpy()-cf.to_numpy()*r.pv_kWp/1000)<TOL,'PV availability')
        require(np.max(h.charge_MW+h.discharge_MW-r.converter_AC_kW/1000)<TOL,'Converter power')
        require(np.max(h.battery_MWh-.9*r.battery_nominal_kWh/1000)<TOL and np.max(.1*r.battery_nominal_kWh/1000-h.battery_MWh)<TOL,'Storage bounds')
        require(h.diesel_MW.max()<=r.diesel_kW/1000+TOL and h.diesel_MW.sum()<=.2*365+TOL,'Diesel bounds')
        require(np.minimum(h.charge_MW,h.discharge_MW).sum()<.001,'No simultaneous cycling')
        loss=0 if r.mode=='standalone' else .08 if r.mode=='mini_grid' else .1
        require(np.max(abs(h.bus_load_MW-h.target_delivered_MW/(1-loss)))<TOL,'Portfolio local losses')
        if r.mode!='grid_extension':require(h.grid_MW.abs().max()<TOL,'Off-grid isolation')
        else:
            sc=r.key.rsplit('_',1)[1];hours=m.CONFIG['scenarios'][sc]['outage_local_hours']
            if hours:require(h.loc[((h.index.hour+2)%24).isin(hours),'grid_MW'].abs().max()<TOL,'Local outage service')
        if r.mode=='standalone':require(h.diesel_MW.abs().max()<TOL,'Standalone diesel prohibition')
        records[r.key]=h
    require(len(table)==30,'Thirty pre-sized portfolios')
    return table,records

def evaluate(only=None):
    complete=only is None
    if complete:require(m.valid(m.OUT),'Regional run hashes')
    for relative,digest in json.loads((m.DATA/'sources.json').read_text()).items():
        require(m.lib.r.sha(m.ROOT/relative)==digest,'Frozen source provenance '+relative)
    coarse=pd.read_csv(m.DATA/'zones_36.csv').groupby('supply_bus')[['connections','baseline_residential_MWh','target_MWh']].sum()
    fine=pd.read_csv(m.DATA/'zones_48.csv').groupby('supply_bus')[['connections','baseline_residential_MWh','target_MWh']].sum()
    require(np.max(abs(coarse-fine).to_numpy())<.01,'Resolution check preserves bus demand and coverage')
    library,hourly=library_checks();summary=pd.read_csv(m.OUT/'summary.csv') if complete else pd.DataFrame([json.loads((m.OUT/only/'summary.json').read_text())])
    if complete:
        # Refinement must not create/discard fixed site fees for an unchanged policy.
        for mode in ['grid','mini_grid','standalone']:
            totals=[]
            for count in [36,48]:
                zz=pd.read_csv(m.DATA/f'zones_{count}.csv')
                totals.append(sum(m.lib.package(z,mode,'selective',library)['local_EAC_USD'] for z in zz.itertuples()))
            require(abs(totals[0]-totals[1])<.1,'Aggregation-neutral site accounting '+mode)
    reference=m.coupled.national_network(np.zeros(8760));rows=[]
    for result in summary.itertuples():
        folder=m.OUT/result.case;require(m.valid(folder),'Case hashes '+result.case)
        n=load_network(folder/'network.nc');error=electrical_checks(n)
        require(not n.generators.carrier.eq('shortage').any(),'No original shortage source')
        deficit=n.generators.index[n.generators.carrier.eq('unserved_diagnostic')]
        unmet=float(n.generators_t.p[deficit].sum().sum())
        diagnostic=result.status=='infeasible_benchmark_diagnostic'
        require(abs(unmet-result.unserved_MWh)<.01,'Explicit unserved energy')
        if not diagnostic:require(len(deficit)==0 and unmet<.01,'Feasible cases have no shortage generator')
        else:require(result.policy!='mixed' and pd.isna(result.annual_system_cost_USD),'Infeasible benchmark is not a feasible-cost comparison')
        zones=pd.read_csv(m.DATA/f'zones_{result.zones}.csv').set_index('zone_id')
        cross=pd.read_csv(m.DATA/f'crosswalk_{result.zones}.csv.gz')
        source=pd.read_csv(m.ROOT/'research/dre_atlas_2025/data/settlement_attributes.csv.gz')
        source=source[source.admin_cgaz_1.isin(m.CONFIG['states'])]
        require(set(cross.geohash)==set(source.geohash) and cross.geohash.is_unique,'Complete geographic coverage')
        require(int(cross.num_connections.sum())==10078666,'Coverage counts')
        grouped=cross.groupby('zone_id').agg(connections=('num_connections','sum'),clusters=('geohash','size'))
        require(np.max(abs(grouped-zones[['connections','clusters']]).to_numpy())<.01,'Crosswalk aggregates match zones')
        require(set(zones.state)==set(m.CONFIG['states']),'All six states')
        chosen=pd.read_csv(folder/'zone_choices.csv').set_index('zone_id');options=pd.read_csv(folder/'options.csv')
        require(set(chosen.index)==set(zones.index),'Every zone selected once')
        require(abs(chosen.target_MWh.sum()-result.target_residential_MWh)<.01,'Target energy')
        require(np.max(abs(chosen.target_MWh-zones.target_MWh*result.demand_factor))<.01,'Scenario demand scaling')
        require(np.min(zones.target_MWh-zones.baseline_residential_MWh)>-.01,'Service uplift is nonnegative')
        for bus in zones.supply_bus.unique():
            for suffix in [' consumption',' losses']:
                require(np.max(abs(n.loads_t.p_set[bus+suffix]-reference.loads_t.p_set[bus+suffix]*(1-m.CONFIG['residential_share'])))<TOL,'Remove residential share exactly once')
            expected=np.zeros(8760)
            for zid,z in chosen[chosen.supply_bus.eq(bus)].iterrows():
                if z['mode']=='grid':expected+=hourly[z.key].grid_MW.to_numpy()*z.scale
            observed=n.loads_t.p_set['service_'+bus]-n.generators_t.p['cancel_'+bus]
            require(np.max(abs(expected-observed))<TOL,'Chosen local/national interface')
        other=[x for x in reference.loads.index if reference.loads.at[x,'bus'] not in zones.supply_bus.unique() and x!='additional_access']
        require(np.max(abs(n.loads_t.p_set[other]-reference.loads_t.p_set[other]).to_numpy())<TOL,'Outside-region background unchanged')
        local_error=0.
        for zid,z in chosen.iterrows():
            h=hourly[z.key]
            local_error=max(local_error,float(np.max(abs((h.pv_MW+h.diesel_MW+h.grid_MW+h.discharge_MW-h.charge_MW-h.bus_load_MW)*z.scale))))
            require(local_error<TOL,'Scaled local hourly balance')
            require(np.max(abs((h.battery_MWh-np.roll(h.battery_MWh,1)-.95*h.charge_MW+h.discharge_MW/.95)*z.scale))<TOL,'Scaled cyclic storage')
            original=options[(options.zone_id==zid)&(options['mode']==z['mode'])].iloc[0]
            require(abs(original.local_EAC_USD-z.local_EAC_USD)<.01,'Selected option cost')
            from types import SimpleNamespace
            zone=SimpleNamespace(zone_id=zid,**zones.loc[zid].to_dict())
            rebuilt=m.lib.package(zone,z['mode'],result.scenario,library,result.demand_factor,result.thermal_cost_factor)
            require(abs(rebuilt['local_EAC_USD']-z.local_EAC_USD)<.1,'Rebuild local ledger from frozen inputs')
            require(abs(rebuilt['initial_USD']-z.initial_USD)<.1,'Rebuild local initial investment')
            protection=0 if z['mode']=='standalone' else z.clusters*float(m.lib.inputs()[1]['annual_security_network']['central'])
            require(abs(z.annual_site_security_USD-protection)<.01,'Site protection counted per source cluster')
            for cap in ['pv_kWp','diesel_kW','battery_nominal_kWh','converter_AC_kW']:
                librow=library.set_index('key').loc[z.key]
                require(abs(z[cap]-librow[cap]*z.scale)<.01,'Scaled fixed portfolio capacity')
            require(abs(z.scale*365-z.target_MWh)<.01,'Scaled delivered service')
            if result.policy=='grid_led':require(z['mode']=='grid','Grid-led restriction')
            if result.policy=='decentralized':require(z['mode']!='grid','Decentralized restriction')
        repairs=pd.read_csv(folder/'repairs.csv').set_index('asset_id')
        require(np.max(abs(repairs.selected-np.round(repairs.selected)))<TOL,'Binary repairs')
        for name,e in repairs.iterrows():
            bound=e.reference_MW*(e.available_fraction+(1-e.available_fraction)*e.selected)
            require(n.links_t.p0[name].abs().max()<=bound+TOL,'Recovered transfer capacity')
        sc=m.CONFIG['scenarios'][result.scenario]
        require(repairs.spend_USD.sum()<=sc['repair_budget_USD']+.01,'Capital budget')
        if sc['force_repairs']:require((repairs.selected>.999).all(),'Restored case projects')
        budgets=pd.read_csv(folder/'hydro_budgets.csv')
        for b in budgets.itertuples():require(n.generators_t.p.loc[n.snapshots.month==b.month,b.generator].sum()<=b.budget_MWh+.1,'Monthly hydro budget')
        national=float((n.generators_t.p.sum()*n.generators.marginal_cost).sum())-unmet*1e6
        params={k:float(v['central']) for k,v in m.lib.inputs()[1].items()}
        factor=m.annuity(params['real_discount_rate'],m.CONFIG['repair_life_years'])+m.CONFIG['repair_annual_om_fraction']
        actual=national+chosen.local_EAC_USD.sum()+repairs.spend_USD.sum()*factor
        reported=result.diagnostic_resource_cost_USD if diagnostic else result.annual_system_cost_USD
        require(abs(actual-reported)<max(1,abs(result.objective_USD)*1e-9),'Whole-system cost reconstruction')
        gap=max(0,(result.objective_USD-result.lower_bound_USD)/abs(result.objective_USD))
        require(gap<=m.CONFIG['mip_gap']+1e-7,'Candidate-library MIP bound')
        require(result.objective_USD>=result.lower_bound_USD-1,'Numerical lower bound')
        require(result.source_clusters==11268 and result.potential_connections==10078666,'Complete case coverage')
        rows.append(dict(case=result.case,status=result.status,bus_balance_max_error_MW=error,local_balance_max_error_MW=local_error,cost_error_USD=actual-reported,relative_bound_gap=gap,
                         hourly_service_met=not diagnostic,unserved_MWh=unmet,source_clusters=11268,zones=result.zones))
    if complete:
        require(len(summary)==12 and summary['case'].is_unique,'Complete experiment set')
        base=summary[(summary.zones==36)&(summary.demand_factor==1)&(summary.thermal_cost_factor==1)]
        for sc,g in base.groupby('scenario'):
            mixed=g[g.policy.eq('mixed')].iloc[0]
            require(mixed.annual_system_cost_USD<=g.annual_system_cost_USD.min()+abs(mixed.objective_USD)*m.CONFIG['mip_gap']+1,'Mixed includes benchmark choices')
        fine=summary[summary.zones.eq(48)].iloc[0]
        coarse=base[base.scenario.eq('selective')&base.policy.eq('mixed')].iloc[0]
        require(fine.annual_system_cost_USD<=coarse.annual_system_cost_USD+abs(fine.objective_USD)*m.CONFIG['mip_gap']+1,'Refinement cannot materially increase optimal candidate cost')
        pd.DataFrame(rows).to_csv(m.OUT/'independent_checks.csv',index=False,lineterminator='\n')
        facts=dict(passed=True,full_year_cases=len(rows),feasible_cases=sum(r['hourly_service_met'] for r in rows),infeasible_benchmarks=sum(not r['hourly_service_met'] for r in rows),normalized_local_designs=30,clusters=11268,states=6,
            hours=8760,primary_zones=36,resolution_check_zones=48,field_validated=False,unrestricted_design_optimum=False,
            interpretation='Fixed-capacity hourly operations checked; infeasible benchmarks explicitly diagnose unserved energy and have no feasible cost reported')
        (m.OUT/'validation.json').write_text(json.dumps(facts,indent=2)+'\n');print(json.dumps(facts));return facts
    print(pd.DataFrame(rows).to_string(index=False));return rows

if __name__=='__main__':evaluate()
