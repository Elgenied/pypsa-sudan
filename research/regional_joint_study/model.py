"""Full-year six-state investment planning, with independently sized off-grid alternatives.

Run through run_study.py for resumable case-level execution and fixed-investment replay.
The network is a transport approximation; physical settlement routing is not optimized.
"""
from pathlib import Path
from dataclasses import dataclass, asdict
from types import SimpleNamespace
import argparse
import copy
import gc
import json
import os
import sys
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE.parent / 'system_costs'))
import regional_model as base
from cost_model import annuity
from check_coupled import load_network
lib = base.lib
OUT = HERE / 'results'
TIEBREAK = .001


@dataclass(frozen=True)
class Case:
    scenario: str
    policy: str = 'mixed'
    zones: int = 36
    demand: float = 1.
    fuel: float = 1.

    @property
    def key(self):
        return f'{self.scenario}_{self.policy}_{self.zones}_d{self.demand:g}_f{self.fuel:g}'


def cases():
    return ([Case(s, p) for s in ['restricted', 'selective', 'restored']
             for p in ['mixed', 'grid_led', 'decentralized']]
            + [Case('selective', zones=48), Case('selective', demand=1.2),
               Case('selective', fuel=1.25)])


def fingerprint(c):
    return dict(case=asdict(c), model=lib.r.sha(Path(__file__)), inherited=base.fingerprints(),
                library_summary=lib.r.sha(lib.OUT / 'summary.csv'))


def valid(folder, fp):
    marker = folder / 'manifest.json'
    if not marker.exists():
        return False
    old = json.loads(marker.read_text())
    return old['inputs'] == fp and all((folder / p).is_file() and lib.r.sha(folder / p) == h
                                      for p, h in old['outputs'].items())


def stamp(folder, fp, names):
    marker = dict(inputs=fp, outputs={p: lib.r.sha(folder / p) for p in names})
    (folder / 'manifest.json').write_text(json.dumps(marker, indent=2), encoding='utf-8')


def offgrid_profile(c, z, mode, library):
    """Reoptimize diesel-capable mini-grids for the fuel check; preserve cached base cases."""
    key = lib.key_for(c.zones, z.zone_id, mode)
    if c.fuel == 1 or mode == 'standalone':
        return library.loc[key], lib.OUT / library.at[key, 'hourly_file']
    folder = OUT / 'offgrid_fuel' / f'{key}_f{c.fuel:g}'
    fp = dict(inputs=fingerprint(c), zone=z.zone_id, mode=mode, fuel=c.fuel)
    if not valid(folder, fp):
        folder.mkdir(parents=True, exist_ok=True)
        site = SimpleNamespace(geohash=z.weather_geohash, village_name=z.zone_id,
            admin_cgaz_1=z.state, num_connections=1000, hull_area=1.,
            distance_to_existing_transmission_lines=0., pv_value=1800.,
            pilot_type='regional_normalized_fuel_check')
        with lib.context(folder):
            def fuel_inputs():
                values = lib.inputs()
                values[1]['diesel_delivered_price']['central'] = str(
                    float(values[1]['diesel_delivered_price']['central']) * c.fuel)
                return values
            lib.p.load_inputs = fuel_inputs
            rec, _, _ = lib.p.solve(site, mode)
        hourly = next(folder.glob('*hourly.csv.gz'))
        rec['key'] = key
        rec['profile_path'] = hourly.relative_to(ROOT).as_posix()
        (folder / 'record.json').write_text(json.dumps(rec, indent=2), encoding='utf-8')
        stamp(folder, fp, ['record.json', hourly.name])
    rec = json.loads((folder / 'record.json').read_text())
    return pd.Series(rec), ROOT / rec['profile_path']


def inputs(c):
    zones = lib.zones(c.zones)
    library = pd.read_csv(lib.OUT / 'summary.csv').set_index('key')
    profiles, alternatives, fixed, initial_fixed = {}, [], {}, {}
    for z in zones.itertuples():
        for mode in ['standalone', 'mini_grid']:
            rec, path = offgrid_profile(c, z, mode, library)
            key = lib.key_for(c.zones, z.zone_id, mode)
            for col in rec.index.intersection(library.columns):
                library.at[key, col] = rec[col]
            option = lib.package(z, mode, c.scenario, library.reset_index(), c.demand, c.fuel)
            option['profile_path'] = path.relative_to(ROOT).as_posix()
            alternatives.append(option)
        grid = lib.package(z, 'grid', c.scenario, library.reset_index(), c.demand, c.fuel, equipment=0)
        fixed[z.zone_id], initial_fixed[z.zone_id] = grid['local_EAC_USD'], grid['initial_USD']
        path = lib.OUT / library.at[lib.key_for(c.zones, z.zone_id, 'grid', c.scenario), 'hourly_file']
        profiles[z.zone_id] = pd.read_csv(path, index_col=0, parse_dates=True)
    alternatives = pd.DataFrame(alternatives)
    off = alternatives.sort_values(['local_EAC_USD', 'mode']).drop_duplicates('zone_id').set_index('zone_id')
    with lib.context(OUT):
        site = SimpleNamespace(num_connections=1000, hull_area=1., distance_to_existing_transmission_lines=0.)
        _, _, _, _, unit, _ = lib.p.cost_context(site, 'grid_extension')
    return zones, library, profiles, alternatives, off, fixed, initial_fixed, unit


def build(c, data):
    zones, library, profiles, alternatives, off, fixed, initial_fixed, unit = data
    n = base.coupled.national_network(np.zeros(8760))
    n.remove('Load', 'additional_access')
    n.add('Carrier', ['electricity', 'local_solar', 'local_battery', 'local_import', 'portfolio_accounting'])
    for bus in zones.supply_bus.unique():
        for suffix in [' consumption', ' losses']:
            n.loads_t.p_set[bus + suffix] *= 1 - base.CONFIG['residential_share']
    n.generators.loc[n.generators.carrier.eq('combustible'), 'marginal_cost'] *= c.fuel
    register = pd.read_csv(base.DATA / 'corridor_register.csv').set_index('asset_id')
    projects = register[register.candidate_repair].copy()
    for name, row in register.iterrows():
        n.links.at[name, 'p_nom'] = row.reference_MW
    availability = pd.Series(1., index=n.snapshots)
    availability.loc[((n.snapshots.hour + 2) % 24).isin(base.CONFIG['scenarios'][c.scenario]['outage_local_hours'])] = 0
    eta_c, eta_d = lib.r.BASE['battery_charge_efficiency'], lib.r.BASE['battery_discharge_efficiency']
    limits = {}
    for z in zones.itertuples():
        zid, scale = z.zone_id, z.target_MWh * c.demand / 365
        h = profiles[zid]
        limits[zid] = dict(pv=5 * scale, battery=30 * scale, converter=5 * scale, grid=scale)
        load = pd.Series(h.target_delivered_MW.to_numpy() * scale / .9, index=n.snapshots)
        n.add('Bus', zid, carrier='electricity', x=z.lon, y=z.lat)
        n.add('Bus', 'battery_' + zid, carrier='local_battery')
        n.add('Load', 'service_' + zid, bus=zid, p_set=load)
        n.add('Generator', 'cancel_' + zid, bus=zid, carrier='portfolio_accounting',
              p_nom_extendable=True, p_nom_max=load.max(), p_min_pu=load / load.max(), p_max_pu=load / load.max())
        n.add('Generator', 'pv_' + zid, bus=zid, carrier='local_solar', p_nom_extendable=True,
              p_nom_max=limits[zid]['pv'], p_max_pu=pd.Series(h.pv_available_pu.to_numpy(), index=n.snapshots),
              capital_cost=unit['pv'] * 1000)
        n.add('Store', 'store_' + zid, bus='battery_' + zid, carrier='local_battery',
              e_nom_extendable=True, e_nom_max=limits[zid]['battery'], e_min_pu=.1, e_max_pu=.9,
              e_cyclic=True, capital_cost=unit['battery'] * 1000)
        n.add('Link', 'charge_' + zid, bus0=zid, bus1='battery_' + zid, carrier='local_battery',
              efficiency=eta_c, p_nom_extendable=True, p_nom_max=limits[zid]['converter'],
              capital_cost=unit['converter'] * 1000, marginal_cost=TIEBREAK)
        n.add('Link', 'discharge_' + zid, bus0='battery_' + zid, bus1=zid, carrier='local_battery',
              efficiency=eta_d, p_nom_extendable=True, p_nom_max=limits[zid]['converter'] / eta_d)
        n.add('Link', 'import_' + zid, bus0=z.supply_bus, bus1=zid, carrier='local_import',
              p_nom_extendable=True, p_nom_max=limits[zid]['grid'], p_max_pu=availability)
    budgets = base.monthly_budgets(n)
    params = {k: float(v['central']) for k, v in lib.inputs()[1].items()}
    annual_factor = annuity(params['real_discount_rate'], base.CONFIG['repair_life_years']) + base.CONFIG['repair_annual_om_fraction']

    def extra(network, sns):
        m = network.model
        one = m.add_variables(lower=1, upper=1, name='constant_one')
        y = m.add_variables(binary=True, coords=[pd.Index(zones.zone_id, name='zone')], name='grid_choice')
        repair = m.add_variables(binary=True, coords=[pd.Index(projects.index, name='project')], name='corridor_repair')
        if c.policy != 'mixed':
            m.add_constraints(y == int(c.policy == 'grid_led'), name='policy')
        if base.CONFIG['scenarios'][c.scenario]['force_repairs']:
            m.add_constraints(repair == 1, name='restored_backbone')
        repair_spend = sum(projects.at[name, 'repair_initial_USD'] * repair.sel(project=name) for name in projects.index)
        m.add_constraints(repair_spend <= base.CONFIG['scenarios'][c.scenario]['repair_budget_USD'], name='repair_budget')
        for name, row in projects.iterrows():
            limit = row.reference_MW * (row.available_fraction + (1 - row.available_fraction) * repair.sel(project=name))
            m.add_constraints(m.variables['Link-p'].sel(name=name) <= limit, name='repair_upper_' + name)
            m.add_constraints(m.variables['Link-p'].sel(name=name) >= -limit, name='repair_lower_' + name)
        cap, flow = m.variables['Link-p_nom'], m.variables['Link-p']
        for z in zones.itertuples():
            zid, lim = z.zone_id, limits[z.zone_id]
            selected = y.sel(zone=zid)
            m.add_constraints(m.variables['Generator-p_nom'].sel(name='cancel_' + zid) == n.loads_t.p_set['service_' + zid].max() * (one - selected), name='cancel_service_' + zid)
            m.add_constraints(m.variables['Generator-p_nom'].sel(name='pv_' + zid) <= lim['pv'] * selected, name='gate_pv_' + zid)
            m.add_constraints(m.variables['Store-e_nom'].sel(name='store_' + zid) <= lim['battery'] * selected, name='gate_battery_' + zid)
            m.add_constraints(cap.sel(name='charge_' + zid) <= lim['converter'] * selected, name='gate_converter_' + zid)
            m.add_constraints(cap.sel(name='import_' + zid) <= lim['grid'] * selected, name='gate_import_' + zid)
            m.add_constraints(cap.sel(name='charge_' + zid) == eta_d * cap.sel(name='discharge_' + zid), name='shared_converter_' + zid)
            m.add_constraints(flow.sel(name='charge_' + zid) + eta_d * flow.sel(name='discharge_' + zid) <= cap.sel(name='charge_' + zid), name='converter_throughput_' + zid)
        add_hydro(network, sns, budgets)
        m.objective += repair_spend * annual_factor + sum(fixed[zid] * y.sel(zone=zid) + off.at[zid, 'local_EAC_USD'] * (one - y.sel(zone=zid)) for zid in zones.zone_id)
    return n, extra, projects, budgets, annual_factor, limits


def add_hydro(n, sns, budgets):
    for b in budgets.itertuples():
        n.model.add_constraints(n.model.variables['Generator-p'].sel(name=b.generator, snapshot=sns[sns.month == b.month]).sum() <= b.budget_MWh,
                                name=b.generator.replace(' ', '_') + f'_month_{b.month}')


def options(solver, log, replay=False):
    if solver == 'gurobi':
        return dict(Threads=4, TimeLimit=7200, MIPGap=.0001, LogToConsole=0, LogFile=str(log))
    return dict(threads=4, time_limit=7200, mip_rel_gap=.0001, log_to_console=False, log_file=str(log), solver='simplex') if replay else dict(threads=4, time_limit=7200, mip_rel_gap=.0001, log_to_console=False, log_file=str(log))


def design_record(c, z, n, library):
    """Rebuild the complete capital/replacement/O&M ledger at optimized capacities."""
    updated = library.copy()
    key = lib.key_for(c.zones, z.zone_id, 'grid', c.scenario)
    scale = z.target_MWh * c.demand / 365
    for col, value in [('pv_kWp', n.generators.at['pv_' + z.zone_id, 'p_nom_opt'] * 1000),
                       ('battery_nominal_kWh', n.stores.at['store_' + z.zone_id, 'e_nom_opt'] * 1000),
                       ('converter_AC_kW', n.links.at['charge_' + z.zone_id, 'p_nom_opt'] * 1000), ('diesel_kW', 0)]:
        updated.at[key, col] = value / scale
    updated.at[key, 'diesel_generation_kWh'] = 0
    rec = lib.package(z, 'grid', c.scenario, updated.reset_index(), c.demand, c.fuel)
    rec['grid_import_MWh'] = float(n.links_t.p0['import_' + z.zone_id].sum())
    rec['diesel_MWh'] = 0.
    rec['profile_path'] = ''
    return rec


def solve(c, solver='gurobi'):
    folder = OUT / c.key
    fp = fingerprint(c)
    if valid(folder, fp):
        print('CACHED', c.key, flush=True)
        return json.loads((folder / 'summary.json').read_text())
    folder.mkdir(parents=True, exist_ok=True)
    data = inputs(c)
    zones, library, profiles, alternatives, off, fixed, _, unit = data
    n, extra, projects, budgets, factor, limits = build(c, data)
    print('SOLVE', c.key, flush=True)
    (folder / 'solver.log').write_text('')
    opt = options(solver, folder / 'solver.log')
    status, term = n.optimize(solver_name=solver, extra_functionality=extra, solver_options=opt)
    if (status, term) != ('ok', 'optimal'):
        (folder / 'failure.json').write_text(json.dumps(dict(status=status, termination=term, case=c.key), indent=2))
        raise RuntimeError(f'{c.key}: {status}/{term}; no completed investment result')
    selection = n.model.variables['grid_choice'].solution.to_series()
    repairs = projects.copy()
    repairs['selected'] = n.model.variables['corridor_repair'].solution.to_series().round().astype(int)
    repairs['spend_USD'] = repairs.selected * repairs.repair_initial_USD
    rows = []
    for z in zones.itertuples():
        rec = design_record(c, z, n, library) if selection[z.zone_id] > .5 else off.loc[z.zone_id].to_dict()
        if selection[z.zone_id] > .5:
            linear = fixed[z.zone_id] + sum(rec[col] * unit[asset] for asset, col in [('pv', 'pv_kWp'), ('battery', 'battery_nominal_kWh'), ('converter', 'converter_AC_kW')])
            assert abs(linear - rec['local_EAC_USD']) < 1
        rec['zone_id'] = z.zone_id
        rec['lon'], rec['lat'] = z.lon, z.lat
        rows.append(rec)
    chosen = pd.DataFrame(rows)
    national = float((n.generators_t.p.sum() * n.generators.marginal_cost).sum())
    cost = float(chosen.local_EAC_USD.sum() + national + repairs.spend_USD.sum() * factor)
    penalty = float(n.links_t.p0.filter(regex='^charge_').sum().sum() * TIEBREAK)
    assert abs(cost + penalty - n.objective) < 2
    if solver == 'gurobi':
        gap, bound = float(n.model.solver_model.MIPGap), float(n.model.solver_model.ObjBound)
    else:
        info = n.model.solver_model.getInfo()
        gap, bound = float(info.mip_gap), float(info.mip_dual_bound)
    summary = dict(case=c.key, **asdict(c), status='optimal_within_reported_gap', solver=solver,
        solver_options=opt, annual_system_cost_USD=cost, local_annual_cost_USD=float(chosen.local_EAC_USD.sum()),
        national_operating_cost_USD=national, annual_repair_cost_USD=float(repairs.spend_USD.sum() * factor),
        initial_local_and_repair_USD=float(chosen.initial_USD.sum() + repairs.spend_USD.sum()),
        repair_investment_USD=float(repairs.spend_USD.sum()), grid_import_MWh=float(chosen.grid_import_MWh.sum()),
        local_diesel_MWh=float(chosen.diesel_MWh.sum()), target_residential_MWh=float(chosen.target_MWh.sum()),
        baseline_allocated_residential_MWh=float(zones.baseline_residential_MWh.sum()),
        source_clusters=int(zones.clusters.sum()), potential_connections=int(zones.connections.sum()),
        mip_gap=gap, resource_cost_lower_bound_USD=bound-sum(v['converter'] for v in limits.values())*8760*TIEBREAK,
        cycling_tiebreak_USD=penalty, hours=8760, unserved_MWh=0.,
        **{mode+'_connections': int(chosen.loc[chosen['mode'].eq(mode), 'connections'].sum()) for mode in ['grid','mini_grid','standalone']})
    chosen.to_csv(folder / 'choices.csv', index=False)
    alternatives.to_csv(folder / 'offgrid_options.csv', index=False)
    repairs.to_csv(folder / 'repairs.csv')
    budgets.to_csv(folder / 'hydro_budgets.csv', index=False)
    n.export_to_netcdf(folder / 'network.nc')
    (folder / 'summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    del n
    gc.collect()
    stamp(folder, fp, ['choices.csv','offgrid_options.csv','repairs.csv','hydro_budgets.csv','network.nc','summary.json','solver.log'])
    print('DONE', c.key, cost, 'gap', gap, flush=True)
    return summary


def replay(c, solver='gurobi'):
    """An independent dispatch solve with every investment and choice held fixed."""
    source = OUT / c.key
    assert valid(source, fingerprint(c))
    folder = source / 'replay'
    fp = dict(investment_manifest=lib.r.sha(source/'manifest.json'), model=lib.r.sha(Path(__file__)))
    if valid(folder, fp):
        print('CACHED REPLAY', c.key, flush=True)
        return
    folder.mkdir(exist_ok=True)
    n = load_network(source / 'network.nc')
    for component, nominal in [('generators','p_nom'),('links','p_nom'),('stores','e_nom')]:
        table = getattr(n, component)
        selected = table[nominal + '_extendable']
        table.loc[selected, nominal] = table.loc[selected, nominal + '_opt'].clip(lower=0)
        table.loc[selected, nominal + '_extendable'] = False
    register = pd.read_csv(base.DATA/'corridor_register.csv').set_index('asset_id')
    repairs = pd.read_csv(source/'repairs.csv').set_index('asset_id')
    for name, row in register.iterrows():
        n.links.at[name,'p_nom'] = row.reference_MW * (row.available_fraction+(1-row.available_fraction)*repairs.at[name,'selected']) if row.candidate_repair else row.reference_MW
    budgets = pd.read_csv(source/'hydro_budgets.csv')
    def extra(network, sns):
        add_hydro(network, sns, budgets)
        for zid in lib.zones(c.zones).zone_id:
            flow = network.model.variables['Link-p']
            network.model.add_constraints(flow.sel(name='charge_'+zid)+.95*flow.sel(name='discharge_'+zid)<=n.links.at['charge_'+zid,'p_nom'], name='fixed_converter_'+zid)
    (folder/'solver.log').write_text('')
    print('REPLAY', c.key, flush=True)
    status, term = n.optimize(solver_name=solver, extra_functionality=extra,
        solver_options=options(solver, folder/'solver.log', True))
    if (status,term)!=('ok','optimal'):
        raise RuntimeError(f'{c.key} fixed-investment replay: {status}/{term}')
    n.export_to_netcdf(folder/'network.nc')
    national = float((n.generators_t.p.sum()*n.generators.marginal_cost).sum())
    original = json.loads((source/'summary.json').read_text())
    assert n.objective <= original['national_operating_cost_USD'] + original['cycling_tiebreak_USD'] + 5
    record = dict(status='optimal_fixed_investments', hours=8760, unserved_MWh=0.,
        national_operating_cost_USD=national, capacity_and_service_choices_fixed=True)
    (folder/'summary.json').write_text(json.dumps(record,indent=2))
    del n
    gc.collect()
    stamp(folder, fp, ['network.nc','summary.json','solver.log'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('case', choices=[c.key for c in cases()])
    parser.add_argument('--solver', choices=['gurobi','highs'], default='gurobi')
    parser.add_argument('--phase', choices=['solve','replay'], default='solve')
    args = parser.parse_args()
    case = next(c for c in cases() if c.key==args.case)
    (solve if args.phase=='solve' else replay)(case, args.solver)
