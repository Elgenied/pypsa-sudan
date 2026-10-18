"""Independent saved-output checks for hourly service, national dispatch and bounds."""
import json
import numpy as np
import pandas as pd
import pypsa
import networkx as nx
import coupled_model as c

TOL=2e-5
def require(x,message):
    if not bool(x):raise AssertionError(message)

def load_network(path):
    n=pypsa.Network(path)
    for component,attrs in [('generators',['p']),('links',['p0','p1']),('stores',['p','e']),('loads',['p_set'])]:
        dynamic=getattr(n,component+'_t');names=getattr(n,component).index
        for attr in attrs:dynamic[attr]=dynamic[attr].reindex(index=n.snapshots,columns=names,fill_value=0.)
    require(n.snapshots.equals(pd.date_range('2022-01-01',periods=8760,freq='h')),'Full UTC year')
    require(np.allclose(n.snapshot_weightings,1),'Unit hourly weights')
    return n

def electrical_checks(n):
    error=0.
    for bus in n.buses.index:
        residual=n.generators_t.p.loc[:,n.generators.bus.eq(bus)].sum(axis=1)-n.loads_t.p_set.loc[:,n.loads.bus.eq(bus)].sum(axis=1)
        residual+=n.stores_t.p.loc[:,n.stores.bus.eq(bus)].sum(axis=1)
        residual-=n.links_t.p0.loc[:,n.links.bus0.eq(bus)].sum(axis=1)+n.links_t.p1.loc[:,n.links.bus1.eq(bus)].sum(axis=1)
        error=max(error,float(residual.abs().max()))
    require(error<TOL,'Bus balance '+str(error))
    for name,g in n.generators.iterrows():
        cap=g.p_nom_opt if g.p_nom_extendable else g.p_nom
        upper=n.generators_t.p_max_pu[name] if name in n.generators_t.p_max_pu else g.p_max_pu
        lower=n.generators_t.p_min_pu[name] if name in n.generators_t.p_min_pu else g.p_min_pu
        require(np.max(n.generators_t.p[name]-cap*upper)<TOL,'Generator upper '+name)
        require(np.max(cap*lower-n.generators_t.p[name])<TOL,'Generator lower '+name)
    for name,l in n.links.iterrows():
        cap=l.p_nom_opt if l.p_nom_extendable else l.p_nom
        require(np.max(n.links_t.p0[name]-cap*l.p_max_pu)<TOL,'Link upper '+name)
        require(np.max(cap*l.p_min_pu-n.links_t.p0[name])<TOL,'Link lower '+name)
        require(np.max(np.abs(n.links_t.p1[name]+l.efficiency*n.links_t.p0[name]))<TOL,'Link loss '+name)
    return error

def national_checks(folder,imports):
    n=load_network(folder/'network.nc');error=electrical_checks(n)
    require(len(n.buses)==19 and len(n.links)==13,'National topology')
    require(not n.generators.carrier.eq('shortage').any(),'No national shortage source')
    reference=pypsa.Network(c.DATA/'national_reference.nc')
    expected=np.roll(reference.loads_t.p_set.to_numpy(),-2,axis=0)
    require(np.max(np.abs(n.loads_t.p_set[reference.loads_t.p_set.columns]-expected).to_numpy())<TOL,'National local-to-UTC shift')
    require(np.max(np.abs(n.loads_t.p_set.additional_access-np.asarray(imports)))<TOL,'National interface demand')
    require(n.loads.at['additional_access','bus']==c.CONFIG['national_bus'],'Interface location')
    facts=pd.read_csv(c.DATA/'national_2022.csv',index_col=0).value
    hydro_budget=facts.gross_hydro/(facts.gross_hydro+facts.gross_combustible+facts.gross_other)*facts.net_generation*1000
    for name,g in n.generators.query("carrier=='hydro'").iterrows():
        budget=hydro_budget*g.p_nom/facts.capacity_hydro
        require(abs(g.e_sum_max-budget)<.01,'Recreated hydro constraint')
        require(n.generators_t.p[name].sum()<=budget+.1,'National annual hydro budget')
    annual_load=float(n.loads_t.p_set.sum().sum());annual_gen=float(n.generators_t.p.sum().sum())
    require(abs(annual_load-annual_gen)<.1,'National annual balance')
    require(abs(annual_load-(facts.consumption+facts.losses)*1000-np.sum(imports))<.1,'No double-counted national background')
    cost=float((n.generators_t.p.sum()*n.generators.marginal_cost).sum())
    result=json.loads((folder/'summary.json').read_text())
    require(abs(cost-result['cost_USD'])<.1,'National generation cost reconstruction')
    require(result['status']=='optimal','National LP status')
    require(result['max_primal_infeasibility']<TOL and result['max_dual_infeasibility']<TOL,'National LP primal/dual feasibility')
    return cost,error

def evaluate(scenarios=None):
    complete=scenarios is None
    scenarios=c.CONFIG['scenario_order'] if complete else list(scenarios)
    if complete:require(c.valid(c.OUT),'Input or output hashes changed')
    else:
        require(c.valid(c.OUT/'offgrid') and c.valid(c.OUT/'national_base'),'Base input/output hashes changed')
        for sc in scenarios:require(c.valid(c.OUT/sc),'Changed or incomplete scenario '+sc)
    sites,routes=c.setup();off=pd.read_csv(c.OUT/'offgrid/summary.csv').set_index(['site_id','mode'])
    profiles={};params={k:float(v['central']) for k,v in c.recovery.inputs()[1].items()}
    diesel_mc=(params['diesel_delivered_price']*params['diesel_specific_fuel']+params['diesel_variable_om'])*1000
    with c.context():
        for s in sites.itertuples(index=False):profiles[s.site_id]=c.pilot.weather_and_load(s)[1:]
    for s in sites.itertuples(index=False):
        cf,load=profiles[s.site_id]
        for mode in ['standalone','mini_grid']:
            o=off.loc[(s.site_id,mode)];h=pd.read_csv(c.OUT/'offgrid'/f'{o.run_id}_hourly.csv.gz')
            require(len(h)==8760,'Off-grid hours')
            require(np.max(abs(h.target_delivered_MW-load.to_numpy()))<TOL,'Off-grid delivered service')
            require(np.max(abs(h.pv_MW+h.diesel_MW+h.discharge_MW-h.charge_MW-h.bus_load_MW))<TOL,'Off-grid power balance')
            require(np.max(abs(h.battery_MWh-np.roll(h.battery_MWh,1)-c.BASE['battery_charge_efficiency']*h.charge_MW+h.discharge_MW/c.BASE['battery_discharge_efficiency']))<TOL,'Off-grid cyclic chronology')
            require(h[['pv_MW','diesel_MW','charge_MW','discharge_MW','battery_MWh']].min().min()>-TOL,'Nonnegative off-grid operation')
            require(np.max(h.pv_MW-cf.to_numpy()*o.pv_kWp/1000)<TOL,'Off-grid PV limit')
            require(np.max(h.diesel_MW-o.diesel_kW/1000)<TOL,'Off-grid diesel limit')
            require(np.max(h.charge_MW+h.discharge_MW-o.converter_AC_kW/1000)<TOL,'Off-grid converter')
            require(np.max(h.battery_MWh-c.BASE['battery_max_soc']*o.battery_nominal_kWh/1000)<TOL,'Off-grid SOC upper')
            require(np.max(c.BASE['battery_min_soc']*o.battery_nominal_kWh/1000-h.battery_MWh)<TOL,'Off-grid SOC lower')
            require(h.diesel_MW.sum()<=load.sum()*c.BASE['diesel_max_fraction_of_delivered_energy']+TOL,'Off-grid fuel budget')
            if mode=='standalone':require(abs(h.diesel_MW).sum()<TOL,'No standalone diesel')
            loss=0 if mode=='standalone' else c.BASE['mini_grid_distribution_loss']
            require(np.max(abs(h.bus_load_MW-load.to_numpy()/(1-loss)))<TOL,'Off-grid distribution losses')
            with c.context():_,q,ledger,_,_,groups=c.pilot.cost_context(s,mode)
            for a,key in [('pv','pv_kWp'),('diesel','diesel_kW'),('battery','battery_nominal_kWh'),('converter','converter_AC_kW')]:
                for item in groups[a]:q[item]=float(o[key])
            actual=ledger(q)
            require(abs(c.recovery.fixed_eac(actual)+h.diesel_MW.sum()*diesel_mc-o.equivalent_annual_cost_USD)<.1,'Off-grid lifecycle cost')
    base_cost,base_error=national_checks(c.OUT/'national_base',np.zeros(8760));rows=[]
    for sc in scenarios:
        folder=c.OUT/sc;summary=json.loads((folder/'summary.json').read_text());selected=folder/summary['selected_iteration']
        n=load_network(selected/'local_network.nc');local_error=electrical_checks(n)
        z=pd.read_csv(selected/'grid_choice.csv',index_col=0).value;y=pd.read_csv(selected/'route_build.csv',index_col=0).value
        meta=json.loads((selected/'master.json').read_text());table=pd.read_csv(selected/'settlements.csv').set_index('site_id')
        for values in [z,y,pd.Series([meta['repair']])]:require(np.max(abs(values-np.round(values)))<TOL,'Integer choices')
        require(abs(z.S1-meta['repair'])<TOL,'Root repair and service')
        graph=nx.Graph();graph.add_nodes_from(sites.site_id)
        for e in routes.itertuples():
            require(y[e.edge_id]<=meta['repair']+TOL,'Route repair gate')
            require(np.max(n.links_t.p0[e.edge_id+'_f']+n.links_t.p0[e.edge_id+'_r']-e.capacity_MW*y[e.edge_id])<TOL,'Shared route capacity')
            if y[e.edge_id]>.5:graph.add_edge(e.from_site,e.to_site)
        reach=nx.node_connected_component(graph,'S1');grid_energy=0.;local_cost=0.;local_initial=0.
        hub=dict(pv_kWp=n.generators.at['hub_pv','p_nom_opt']*1000,diesel_kW=n.generators.at['hub_diesel','p_nom_opt']*1000,battery_nominal_kWh=n.stores.at['hub_battery','e_nom_opt']*1000,converter_AC_kW=n.links.at['charge','p_nom_opt']*1000)
        for s in sites.itertuples(index=False):
            sid=s.site_id;cf,load=profiles[sid]
            require(np.max(abs(n.loads_t.p_set[sid+'_grid_equivalent']-load/(1-c.BASE['grid_distribution_loss'])))<TOL,'Grid-side service target')
            require(np.max(abs(n.generators_t.p[sid+'_offgrid_column']-load/(1-c.BASE['grid_distribution_loss'])*(1-z[sid])))<TOL,'Exact off-grid accounting column')
            if z[sid]>.5:
                require(sid in reach and meta['repair']>.5,'Grid root connectivity')
                require(table.at[sid,'choice']=='grid','Reported grid choice');grid_energy+=load.sum()
                with c.context():_,q,ledger,_,_,groups=c.pilot.cost_context(s,'grid_extension')
                q.update(mv_line=0,fuel_tank_ats=1 if sid=='S1' else 0,transformer_100kVA=max(1,np.ceil(load.max()/(.08*(1-c.BASE['grid_distribution_loss'])))))
                caps=hub if sid=='S1' else {k:0. for k in hub}
                for a,key in [('pv','pv_kWp'),('diesel','diesel_kW'),('battery','battery_nominal_kWh'),('converter','converter_AC_kW')]:
                    require(abs(caps[key]-table.at[sid,key])<.01,'Reported hub capacity')
                    for item in groups[a]:q[item]=max(0,caps[key])
                actual=ledger(q);cost=c.recovery.fixed_eac(actual)+(n.generators_t.p.hub_diesel.sum()*diesel_mc if sid=='S1' else 0);initial=actual['summary']['initial_budget_USD']
            else:
                options=off.loc[sid];chosen=options.loc[table.at[sid,'choice']]
                require(chosen.equivalent_annual_cost_USD<=options.equivalent_annual_cost_USD.min()+.1,'Off-grid dominance')
                cost=chosen.equivalent_annual_cost_USD;initial=chosen.initial_budget_USD
            require(abs(cost-table.at[sid,'local_EAC_USD'])<.1,'Local cost reconstruction');local_cost+=cost;local_initial+=initial
        energy=n.stores_t.e.hub_battery;charge=n.links_t.p0.charge;discharge=-n.links_t.p1.discharge
        storage_error=float(np.max(abs(energy-np.roll(energy,1)-c.BASE['battery_charge_efficiency']*charge+discharge/c.BASE['battery_discharge_efficiency'])))
        require(storage_error<TOL,'Local battery chronology')
        capacity=n.stores.at['hub_battery','e_nom_opt'];converter=n.links.at['charge','p_nom_opt']
        require(np.max(energy-capacity*c.BASE['battery_max_soc'])<TOL and np.max(capacity*c.BASE['battery_min_soc']-energy)<TOL,'Local SOC')
        require(np.max(charge+discharge-converter)<TOL,'Local converter throughput')
        require(abs(converter-c.BASE['battery_discharge_efficiency']*n.links.at['discharge','p_nom_opt'])<TOL,'Converter rating')
        require(np.minimum(charge,discharge).sum()<.001,'No simultaneous cycling')
        require(n.generators_t.p.hub_diesel.sum()<=grid_energy*c.BASE['diesel_max_fraction_of_delivered_energy']+TOL,'Grid fuel limit')
        for name in ['hub_pv','hub_diesel']:
            g=n.generators.loc[name];require(g.p_nom_opt<=g.p_nom_max*meta['repair']+TOL,'Hub capacity gate')
            if meta['repair']>.5:require(g.p_nom_opt<g.p_nom_max*.999,'Artificial generator bound binds')
        require(capacity<=n.stores.at['hub_battery','e_nom_max']*meta['repair']+TOL,'Storage gate')
        require(converter<=n.links.at['charge','p_nom_max']*meta['repair']+TOL,'Converter gate')
        require(np.max(n.links_t.p0.common_feeder-c.CONFIG['common_feeder_capacity_MW']*meta['repair'])<TOL,'Feeder gate')
        imports=n.generators_t.p.national_import.to_numpy()
        available=(~((n.snapshots.hour+2)%24).isin(c.CONFIG['scenarios'][sc]['outage_local_hours'])).astype(float)
        require(np.max(imports-c.CONFIG['common_feeder_capacity_MW']*available)<TOL,'Recovery availability')
        require(np.max(abs(imports-n.links_t.p0.common_feeder))<TOL,'Coupled interface balance')
        national_cost,national_error=national_checks(selected/'national',imports)
        repair=c.infrastructure_cost('mv_line',repair_km=c.CONFIG['common_feeder_repair_km'])
        spend=repair['initial']*meta['repair'];require(spend<=c.CONFIG['scenarios'][sc]['repair_budget_USD']+.1,'Repair budget')
        shared=repair['eac']*meta['repair'];initial_shared=spend
        for e in routes.itertuples():
            rc=c.infrastructure_cost('mv_line',e.route_km);shared+=rc['eac']*y[e.edge_id];initial_shared+=rc['initial']*y[e.edge_id]
        actual=local_cost+shared+national_cost-base_cost
        require(abs(actual-summary['equivalent_annual_access_cost_USD'])<.2,'Incremental whole-system cost')
        require(abs(local_initial+initial_shared-summary['initial_local_investment_USD'])<.2,'Initial cost')
        penalty=charge.sum()*.001
        require(abs(actual+penalty-summary['feasible_upper_bound_USD'])<.2,'Feasible upper bound')
        convergence=pd.read_csv(folder/'convergence.csv')
        require(abs(convergence.master_lower_bound.max()-summary['lower_bound_USD'])<.2,'MIP-based lower bound')
        gap=max(0,summary['feasible_upper_bound_USD']-summary['lower_bound_USD'])
        require(gap<=max(c.CONFIG['coupling_absolute_tolerance_USD'],c.CONFIG['coupling_relative_tolerance']*abs(summary['feasible_upper_bound_USD']))+.2,'Certified coupling tolerance')
        prices=pd.read_csv(folder/'cut_prices.csv.gz');cut_imports=pd.read_csv(folder/'cut_imports.csv.gz');cut_meta=json.loads((folder/'cuts.json').read_text())
        for j,cut in enumerate(cut_meta):
            require(abs(cut['intercept']-(cut['cost_delta']-np.dot(prices[f'price_{j}'],cut_imports[f'import_{j}'])))<.01,'Supporting cut intercept')
            for iteration in sorted(folder.glob('iteration_*')):
                h=pd.read_csv(iteration/'national/interface.csv.gz');q=json.loads((iteration/'national/summary.json').read_text())['cost_USD']-base_cost
                require(cut['intercept']+np.dot(prices[f'price_{j}'],h.import_MW)<=q+.2,'Observed supporting lower bound')
        rows.append(dict(scenario=sc,hours=8760,settlements=len(sites),local_balance_error_MW=local_error,national_balance_error_MW=national_error,storage_error_MWh=storage_error,cost_reconstruction_error_USD=actual-summary['equivalent_annual_access_cost_USD'],coupling_gap_USD=gap))
    if not complete:
        result=dict(passed=True,scope='Completed-case check only; full study is not yet validated',scenarios=scenarios,checks=rows)
        print(json.dumps(result));return result
    summary=pd.read_csv(c.OUT/'summary.csv')
    require(np.max(np.diff(summary.equivalent_annual_access_cost_USD))<1,'Nested local recovery cost')
    require(summary.iloc[0].national_import_MWh<TOL and summary.iloc[0].grid_connections==0,'No-repair limiting case')
    pd.DataFrame(rows).to_csv(c.OUT/'independent_checks.csv',index=False,lineterminator='\n')
    result=dict(passed=True,clusters=len(sites),potential_connections=int(sites.num_connections.sum()),scenarios=3,hours=8760,national_buses=19,national_corridors=13,offgrid_designs=16,all_hourly_service_met=True,national_shortage_allowed=False,coupling_bounds_checked=True,national_allocation=False,field_validated=False)
    (c.OUT/'validation.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result));return result

if __name__=='__main__':evaluate()
