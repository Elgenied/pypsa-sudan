"""Reconstruct saved decisions, hourly constraints and lifecycle costs independently."""
import json
import numpy as np
import pandas as pd
import pypsa
import recovery_model as r
from cost_model import annuity

TOL=2e-6

def require(condition,message):
    if not bool(condition):raise AssertionError(message)

def evaluate():
    manifest=json.loads((r.OUT/'manifest.json').read_text())
    require(manifest['inputs']==r.fingerprints(),'Inputs changed since optimization')
    for path,digest in manifest['outputs'].items():require(r.sha(r.OUT/path)==digest,'Changed output '+path)
    sites,routes,params=r.setup();off=pd.read_csv(r.OUT/'offgrid/summary.csv').set_index(['site_id','mode'])
    summary=pd.read_csv(r.OUT/'summary.csv');checks=[]
    profiles={}
    with r.context():
        for s in sites.itertuples():profiles[s.site_id]=r.pilot.weather_and_load(s)[1:]
    # Check all independent off-grid columns from their exported hourly operation.
    for s in sites.itertuples():
        for mode in r.MODES[:2]:
            rec=off.loc[(s.site_id,mode)]
            h=pd.read_csv(r.OUT/'offgrid'/f'{rec.run_id}_hourly.csv.gz')
            require(len(h)==8760,'Incomplete offgrid year')
            cf,load=profiles[s.site_id]
            require(np.max(np.abs(h.target_delivered_MW-load.to_numpy()))<TOL,'Offgrid service mismatch')
            require(np.max(np.abs(h.pv_MW+h.diesel_MW+h.discharge_MW-h.charge_MW-h.bus_load_MW))<TOL,'Offgrid balance')
            require(np.max(np.abs(h.battery_MWh-np.roll(h.battery_MWh,1)-r.BASE['battery_charge_efficiency']*h.charge_MW+h.discharge_MW/r.BASE['battery_discharge_efficiency']))<TOL,'Offgrid storage chronology')
            require(float(h[['pv_MW','diesel_MW','charge_MW','discharge_MW','battery_MWh']].min().min())>=-TOL,'Negative offgrid operation')
            require(np.max(h.pv_MW-cf.to_numpy()*rec.pv_kWp/1000)<TOL,'Offgrid PV bound')
            require(np.max(h.charge_MW+h.discharge_MW-rec.converter_AC_kW/1000)<TOL,'Offgrid converter bound')
            require(np.max(h.battery_MWh-r.BASE['battery_max_soc']*rec.battery_nominal_kWh/1000)<TOL,'Offgrid SOC upper')
            require(np.max(r.BASE['battery_min_soc']*rec.battery_nominal_kWh/1000-h.battery_MWh)<TOL,'Offgrid SOC lower')
            require(h.diesel_MW.sum()<=load.sum()*r.BASE['diesel_max_fraction_of_delivered_energy']+TOL,'Offgrid diesel budget')
            require(np.max(h.diesel_MW-rec.diesel_kW/1000)<TOL,'Offgrid diesel capacity')
            if mode=='standalone':require(abs(h.diesel_MW).sum()<TOL,'Standalone diesel prohibited')
            loss=0 if mode=='standalone' else r.BASE['mini_grid_distribution_loss']
            require(np.max(np.abs(h.bus_load_MW-load.to_numpy()/(1-loss)))<TOL,'Offgrid distribution loss')
            with r.context():_,q,ledger,_,_,groups=r.pilot.cost_context(s,mode)
            for asset,key in [('pv','pv_kWp'),('diesel','diesel_kW'),('battery','battery_nominal_kWh'),('converter','converter_AC_kW')]:
                for item in groups[asset]:q[item]=float(rec[key])
            actual=ledger(q)
            diesel_mc=(params['diesel_delivered_price']*params['diesel_specific_fuel']+params['diesel_variable_om'])*1000
            cost=r.fixed_eac(actual)+h.diesel_MW.sum()*diesel_mc
            require(abs(cost-rec.equivalent_annual_cost_USD)<.1,'Offgrid cost reconstruction')
    for scenario in r.CONFIG['scenario_order']:
        folder=r.OUT/scenario;sc=r.CONFIG['scenarios'][scenario]
        n=pypsa.Network(folder/'network.nc')
        # PyPSA omits all-default (zero) dynamic columns from NetCDF exports.
        for component,attrs in [('generators',['p']),('links',['p0','p1']),('stores',['p','e'])]:
            dynamic=getattr(n,component+'_t');names=getattr(n,component).index
            for attr in attrs:dynamic[attr]=dynamic[attr].reindex(index=n.snapshots,columns=names,fill_value=0.)
        require(n.snapshots.equals(pd.date_range('2022-01-01',periods=8760,freq='h')),'Time index')
        require(np.allclose(n.snapshot_weightings,1),'Hourly weights')
        z=pd.read_csv(folder/'service_choice.csv',index_col=0).value
        y=pd.read_csv(folder/'route_build.csv',index_col=0).value
        repairs=pd.read_csv(folder/'repair_asset.csv',index_col=0).value
        row=json.loads((folder/'summary.json').read_text())
        for binary in [z,y,repairs]:require(np.max(np.abs(binary-np.round(binary)))<TOL,'Fractional decision')
        table=pd.read_csv(folder/'settlements.csv').set_index('site_id')
        # Full bus balances, independently reconstructed from all incident components.
        max_balance=0.
        for bus in n.buses.index:
            balance=pd.Series(0.,index=n.snapshots)
            balance+=n.generators_t.p.loc[:,n.generators.bus==bus].sum(axis=1)
            balance-=n.loads_t.p_set.loc[:,n.loads.bus==bus].sum(axis=1)
            balance+=n.stores_t.p.loc[:,n.stores.bus==bus].sum(axis=1)
            balance-=n.links_t.p0.loc[:,n.links.bus0==bus].sum(axis=1)
            balance-=n.links_t.p1.loc[:,n.links.bus1==bus].sum(axis=1)
            max_balance=max(max_balance,float(balance.abs().max()))
        require(max_balance<TOL,'Nodal balance')
        max_storage=0.;local_cost=0.;local_initial=0.;grid_energy=0.
        reach={'S1'}
        for _ in sites.site_id:
            for edge in routes.itertuples():
                if y[edge.edge_id]>.5 and (edge.from_site in reach or edge.to_site in reach):reach.update([edge.from_site,edge.to_site])
        for s in sites.itertuples():
            sid=s.site_id;cf,load=profiles[sid];zg=z[sid+'_grid']
            require(abs(sum(z[sid+'_'+mode] for mode in r.MODES)-1)<TOL,'One service choice')
            require(z[sid+'_'+table.at[sid,'choice']]>.5,'Reported service choice')
            for mode in r.MODES[:2]:require(np.max(np.abs(n.generators_t.p[sid+'_'+mode]-load*z[sid+'_'+mode]))<TOL,'Portfolio delivery')
            require(np.max(np.abs(-n.links_t.p1[sid+'_delivery']-load*zg))<TOL,'Grid service delivery')
            if zg>.5:require(repairs.feeder>.5 and sid in reach,'Disconnected grid option')
            store=n.stores.at[sid+'_storage','e_nom_opt'];energy=n.stores_t.e[sid+'_storage']
            charge=n.links_t.p0[sid+'_charge'];discharge=-n.links_t.p1[sid+'_discharge']
            residual=energy-np.roll(energy,1)-r.BASE['battery_charge_efficiency']*charge+discharge/r.BASE['battery_discharge_efficiency']
            max_storage=max(max_storage,float(np.abs(residual).max()))
            require(np.max(energy-r.BASE['battery_max_soc']*store)<TOL,'Storage upper')
            require(np.max(r.BASE['battery_min_soc']*store-energy)<TOL,'Storage lower')
            require(np.minimum(charge,discharge).sum()<1e-3,'Simultaneous battery cycling')
            converter=n.links.at[sid+'_charge','p_nom_opt']
            require(abs(converter-r.BASE['battery_discharge_efficiency']*n.links.at[sid+'_discharge','p_nom_opt'])<TOL,'Converter rating')
            require(np.max(charge+discharge-converter)<TOL,'Converter throughput')
            require(converter<=n.links.at[sid+'_charge','p_nom_max']*zg+TOL,'Converter activation')
            require(store<=n.stores.at[sid+'_storage','e_nom_max']*zg+TOL,'Storage activation')
            for asset in ['pv','diesel']:
                cap=n.generators.at[sid+'_'+asset,'p_nom_opt']
                require(cap<=n.generators.at[sid+'_'+asset,'p_nom_max']*zg+TOL,'Generator activation')
                if n.generators.at[sid+'_'+asset,'p_nom_max']>0 and zg>.5:require(cap<n.generators.at[sid+'_'+asset,'p_nom_max']*.999,'Artificial generator capacity binds')
            if zg>.5:
                if sid=='S1':
                    require(store<n.stores.at[sid+'_storage','e_nom_max']*.999,'Artificial energy bound binds')
                    require(converter<n.links.at[sid+'_charge','p_nom_max']*.999,'Artificial converter bound binds')
                with r.context():_,q,ledger,_,_,groups=r.pilot.cost_context(s,'grid_extension')
                q.update(mv_line=0,transformer_100kVA=max(1,np.ceil(load.max()/(.08*(1-r.BASE['grid_distribution_loss'])))),fuel_tank_ats=1 if sid=='S1' else 0)
                caps=dict(pv=n.generators.at[sid+'_pv','p_nom_opt']*1000,diesel=n.generators.at[sid+'_diesel','p_nom_opt']*1000,battery=store*1000,converter=converter*1000)
                for asset,items in groups.items():
                    for item in items:q[item]=max(0,caps[asset])
                actual=ledger(q);cost=r.fixed_eac(actual)+n.generators_t.p[sid+'_diesel'].sum()*n.generators.at[sid+'_diesel','marginal_cost']
                initial=actual['summary']['initial_budget_USD'];grid_energy+=load.sum()
            else:
                chosen=off.loc[(sid,table.at[sid,'choice'])];cost=float(chosen.equivalent_annual_cost_USD);initial=float(chosen.initial_budget_USD)
            require(abs(cost-table.at[sid,'local_equipment_and_operation_EAC_USD'])<.1,'Local reported EAC')
            local_cost+=cost;local_initial+=initial
        require(max_storage<TOL,'Battery chronology')
        for name,g in n.generators.iterrows():
            availability=n.generators_t.p_max_pu[name] if name in n.generators_t.p_max_pu else g.p_max_pu
            require(np.max(n.generators_t.p[name]-g.p_nom_opt*availability)<TOL,'Generator hourly capacity '+name)
            require(n.generators_t.p[name].min()>-TOL,'Negative generation')
        require(n.links_t.p0.min().min()>-TOL,'Negative directional flow')
        for name,link in n.links.iterrows():
            require(np.max(np.abs(n.links_t.p1[name]+link.efficiency*n.links_t.p0[name]))<TOL,'Link loss accounting '+name)
            require(n.links_t.p0[name].max()<=link.p_nom_opt+TOL,'Link hourly capacity '+name)
        require(n.generators_t.p.filter(like='_diesel').sum().sum()<=grid_energy*r.BASE['diesel_max_fraction_of_delivered_energy']+TOL,'Aggregate grid diesel budget')
        avail=(~((n.snapshots.hour+2)%24).isin(sc['outage_local_hours'])).astype(float)
        require(np.max(n.generators_t.p.restored_supply-r.CONFIG['upstream_repaired_capacity_MW']*avail*repairs.upstream)<TOL,'Upstream repair gate')
        require(np.max(n.links_t.p0.common_feeder-r.CONFIG['common_feeder_capacity_MW']*repairs.feeder)<TOL,'Common feeder repair gate')
        require(repairs.feeder<=z['S1_grid']+TOL,'Grid hub requires anchor service')
        background=n.loads_t.p_set.existing_background
        require(abs(background.max()-r.CONFIG['background_peak_MW'])<TOL,'Background demand unchanged')
        require(np.max(n.generators_t.p.background_backup-background)<TOL,'Dedicated backup limit')
        require(np.max(n.links_t.p0.common_feeder-n.generators_t.p.existing_supply-n.generators_t.p.restored_supply)<TOL,'Grid supplied by bulk interface')
        shared_eac=0.;shared_initial=0.
        for edge in routes.itertuples():
            require(np.max(n.links_t.p0[edge.edge_id+'_f']+n.links_t.p0[edge.edge_id+'_r']-edge.capacity_MW*y[edge.edge_id])<TOL,'Shared edge capacity')
            c=r.infrastructure_cost('mv_line',edge.route_km);shared_eac+=c['eac']*y[edge.edge_id];shared_initial+=c['initial']*y[edge.edge_id]
        repair_costs=dict(feeder=r.infrastructure_cost('mv_line',repair_km=r.CONFIG['common_feeder_repair_km']),upstream=r.infrastructure_cost('upstream_repair'))
        spend=sum(repair_costs[k]['initial']*repairs[k] for k in repair_costs)
        require(spend<=sc['repair_budget_USD']+.1,'Repair budget')
        for k in repair_costs:shared_eac+=repair_costs[k]['eac']*repairs[k];shared_initial+=repair_costs[k]['initial']*repairs[k]
        bg=r.infrastructure_cost('diesel_genset',r.CONFIG['background_peak_MW']*1000);tank=r.infrastructure_cost('fuel_tank_ats')
        regional=sum(n.generators_t.p[k].sum()*n.generators.at[k,'marginal_cost'] for k in ['existing_supply','restored_supply','background_backup'])
        cost=local_cost+shared_eac+regional+bg['eac']+tank['eac']
        require(abs(cost-row['equivalent_annual_cost_USD'])<.1,'Total EAC')
        require(abs(cost/annuity(params['real_discount_rate'],params['horizon_years'])-row['lifecycle_NPC_USD'])<1,'NPC')
        require(abs(local_initial+shared_initial+bg['initial']+tank['initial']-row['initial_investment_USD'])<.1,'Total upfront cost')
        require(row['mip_relative_gap']<=r.CONFIG['mip_relative_gap']+1e-7,'MIP optimality gap')
        require(row['mip_dual_bound_USD']<=row['objective_excluding_background_fixed_USD']+.1,'MIP lower bound')
        checks.append(dict(scenario=scenario,hours=len(n.snapshots),max_bus_balance_error_MW=max_balance,max_storage_error_MWh=max_storage,cost_reconstruction_error_USD=cost-row['equivalent_annual_cost_USD'],repair_spend_USD=spend,connected_grid_sites=sum(z[sid+'_grid']>.5 for sid in sites.site_id),mip_relative_gap=row['mip_relative_gap']))
    # These three feasible sets are nested: larger repair budgets/supply and fewer unavailable hours.
    require(np.max(np.diff(summary.equivalent_annual_cost_USD))<.1,'Improved recovery increased optimal cost')
    require(summary.iloc[0].grid_connections==0 and summary.iloc[0].repair_spend_USD<.1,'Zero-budget limiting case')
    pd.DataFrame(checks).to_csv(r.OUT/'independent_checks.csv',index=False,lineterminator='\n')
    result=dict(passed=True,scenarios=3,settlements=len(sites),potential_connections=int(sites.num_connections.sum()),
        hours_per_scenario=8760,settlement_service_hours=3*len(sites)*8760,offgrid_designs_checked=len(off),
        discrete_choices_checked=True,shared_routes_costed_once=True,repair_budgets_checked=True,
        lifecycle_and_hourly_balances_checked=True,zero_budget_limiting_case_checked=True,nested_recovery_cost_monotonicity_checked=True,
        national_model=False,field_validated=False,measured_damage_used=False)
    (r.OUT/'validation.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result));return result

if __name__=='__main__':evaluate()
