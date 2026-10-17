"""Transparent lifecycle costing of fixed illustrative electrification designs.

No capacity optimization, dispatch, reliability certification or geographic selection.
All currency calculations use editable constant-2025-USD planning assumptions.
"""
from pathlib import Path
import csv
import json
import math
import hashlib

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / 'data/system_costs'
RESULTS = Path(__file__).resolve().parent / 'results'
SCENARIOS = {'lower_input': 'low_USD', 'central': 'base_USD', 'higher_input': 'high_USD'}


def read_csv(path):
    with Path(path).open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def write_csv(path, rows):
    rows = list(rows)
    if not rows:
        raise ValueError('Cannot export an empty result')
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, list(rows[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)


def annuity(rate, years):
    if not math.isfinite(rate) or rate < 0 or years <= 0:
        raise ValueError('Nonnegative real rate and positive years required')
    return 1 / years if rate == 0 else rate / (1 - (1 + rate) ** (-years))


def load_inputs(data=DATA):
    c = read_csv(data / 'components.csv')
    p = read_csv(data / 'scenario_parameters.csv')
    d = read_csv(data / 'case_designs.csv')
    b = read_csv(data / 'bill_of_quantities.csv')
    for rows, key in [(c, 'component'), (p, 'parameter'), (d, 'case')]:
        if len({r[key] for r in rows}) != len(rows):
            raise ValueError(f'Duplicate {key}')
    for row in c:
        for field in ('low_USD', 'base_USD', 'high_USD', 'life_years', 'annual_om_fraction',
                      'imported', 'transport_eligible', 'labour_eligible'):
            row[field] = float(row[field])
            if not math.isfinite(row[field]) or row[field] < 0:
                raise ValueError(f'Invalid {field}: {row["component"]}')
        if row['life_years'] < 1 or not row['life_years'].is_integer():
            raise ValueError('Asset lives must be positive integer years')
        for field in ('imported', 'transport_eligible', 'labour_eligible'):
            if row[field] not in (0, 1):
                raise ValueError('Cost eligibility flags must be 0 or 1')
        if not row['low_USD'] <= row['base_USD'] <= row['high_USD']:
            raise ValueError('Unit-cost range is not ordered')
    for row in d:
        for field in ('connections', 'daily_kWh_per_connection', 'distribution_loss_fraction',
                      'diesel_generation_fraction', 'repair_mv_route_km', 'repair_cost_fraction'):
            row[field] = float(row[field])
    quantities = {r['case']: {} for r in d}
    for row in b:
        if row['case'] not in quantities or row['component'] not in {r['component'] for r in c}:
            raise ValueError('Unknown bill-of-quantities key')
        if row['component'] in quantities[row['case']]:
            raise ValueError('Duplicate bill-of-quantities row')
        q = float(row['quantity'])
        if not math.isfinite(q) or q < 0:
            raise ValueError('Invalid quantity')
        quantities[row['case']][row['component']] = q
    return {r['component']: r for r in c}, {r['parameter']: r for r in p}, {r['case']: r for r in d}, quantities


def validate_parameters(p):
    for key, value in p.items():
        if not math.isfinite(value) or value < 0:
            raise ValueError(f'Invalid parameter {key}')
    for key in ('horizon_years', 'battery_life_years', 'loan_tenor_years'):
        if p[key] < 1 or int(p[key]) != p[key]:
            raise ValueError(f'{key} must be positive integer')
    for key in ('debt_share', 'grant_share', 'salvage_fraction'):
        if not 0 <= p[key] <= 1:
            raise ValueError(f'{key} outside 0..1')
    if p['debt_share'] + p['grant_share'] > 1:
        raise ValueError('Debt plus grant exceeds initial funding')
    if not 0 < p['collection_fraction'] <= 1:
        raise ValueError('Collection fraction outside (0,1]')
    if p['loan_tenor_years'] > p['horizon_years']:
        raise ValueError('This example requires loan tenor <= study horizon')


def installed_package(items, p, initial):
    """Items carry hardware OR installed prices. Percentages have explicit bases."""
    base = sum(x['cost'] for x in items)
    imported = sum(x['cost'] * x['imported'] for x in items)
    freight = imported * p['international_freight']
    inland = sum(x['cost'] * x['transport_eligible'] for x in items) * p['inland_logistics']
    labour = sum(x['cost'] * x['labour_eligible'] for x in items) * p['equipment_installation']
    direct = base + freight + inland + labour
    engineering = direct * p['engineering_development'] if initial else 0
    contingency = (direct + engineering) * p['contingency']
    taxes = (imported + freight) * p['nonrecoverable_tax']
    # Tax is not marked up by engineering/contingency; logistics are not charged twice.
    return dict(component_purchase=base, international_freight=freight, inland_logistics=inland,
                installation_labour=labour, engineering_development=engineering,
                contingency=contingency, assumed_tax=taxes)


def evaluate(case='mini_grid', scenario='central', overrides=None, quantity_overrides=None,
             design_overrides=None, inputs=None):
    components, parameters, designs, quantities = inputs or load_inputs()
    if scenario not in SCENARIOS or case not in designs:
        raise ValueError('Unknown scenario or case')
    p = {key: float(row[scenario]) for key, row in parameters.items()}
    if set(overrides or {}) - p.keys():
        raise ValueError('Unknown parameter override')
    p.update(overrides or {})
    validate_parameters(p)
    design = dict(designs[case])
    if set(design_overrides or {}) - design.keys():
        raise ValueError('Unknown design override')
    design.update(design_overrides or {})
    for key in ('connections', 'daily_kWh_per_connection', 'distribution_loss_fraction',
                'diesel_generation_fraction', 'repair_mv_route_km', 'repair_cost_fraction'):
        if not math.isfinite(design[key]):
            raise ValueError(f'Nonfinite design input {key}')
    q = dict(quantities[case]); q.update(quantity_overrides or {})
    if set(q) - components.keys():
        raise ValueError('Unknown component override')
    for key, value in q.items():
        if not math.isfinite(value) or value < 0:
            raise ValueError(f'Invalid quantity: {key}')
    if design['connections'] <= 0 or design['daily_kWh_per_connection'] <= 0:
        raise ValueError('Positive demand and connections required')
    if not 0 <= design['distribution_loss_fraction'] < 1:
        raise ValueError('Distribution loss outside [0,1)')
    if not 0 <= design['diesel_generation_fraction'] <= 1:
        raise ValueError('Diesel share outside [0,1]')
    if design['repair_mv_route_km'] < 0 or not 0 <= design['repair_cost_fraction'] <= 1:
        raise ValueError('Invalid repair assumptions')
    if q.get('shs_hybrid_inverter', 0) and q.get('pv_inverter', 0):
        raise ValueError('Standalone hybrid includes MPPT: do not also charge PV inverter')
    items = []
    for key, quantity in q.items():
        if not quantity:
            continue
        row = components[key]
        life = int(p['battery_life_years'] if key == 'battery' else row['life_years'])
        items.append(dict(component=key, group=row['group'], quantity=quantity,
                          quantity_unit=row['quantity_unit'], unit_cost=row[SCENARIOS[scenario]],
                          cost=quantity * row[SCENARIOS[scenario]], life=life,
                          om_fraction=row['annual_om_fraction'],
                          imported=row['imported'], transport_eligible=row['transport_eligible'],
                          labour_eligible=row['labour_eligible']))
    if design['repair_mv_route_km']:
        mv = components['mv_line']
        items.append(dict(component='mv_repair', group='Recovery', quantity=design['repair_mv_route_km'],
                          quantity_unit='repaired_route_km', unit_cost=mv[SCENARIOS[scenario]] * design['repair_cost_fraction'],
                          cost=design['repair_mv_route_km'] * mv[SCENARIOS[scenario]] * design['repair_cost_fraction'],
                          life=20, om_fraction=mv['annual_om_fraction'], imported=0,
                          transport_eligible=0, labour_eligible=0))
    if not items:
        raise ValueError('Empty design')
    initial = installed_package(items, p, initial=True)
    capex = sum(initial.values())
    T = int(p['horizon_years']); rate = p['real_discount_rate']
    energy = design['connections'] * design['daily_kWh_per_connection'] * 365
    sent_out = energy / (1 - design['distribution_loss_fraction'])
    diesel_kWh = sent_out * design['diesel_generation_fraction']
    if diesel_kWh and not q.get('diesel_genset', 0):
        raise ValueError('Diesel generation assumed without a generator')
    if q.get('diesel_genset', 0) and diesel_kWh > q['diesel_genset'] * 8760:
        raise ValueError('Annual diesel generation exceeds nameplate-hour bound')
    grid_kWh = sent_out if case.startswith('grid_') else 0
    operating = {
        'technical_maintenance': sum(x['cost'] * x['om_fraction'] for x in items),
        'insurance_allowance': sum(x['cost'] for x in items) * p['insurance_fraction'],
        'administration': design['connections'] * p['annual_admin_standalone' if case == 'standalone' else 'annual_admin_network'],
        'security_allowance': 0 if case == 'standalone' else p['annual_security_network'],
        'diesel_fuel': diesel_kWh * p['diesel_specific_fuel'] * p['diesel_delivered_price'],
        'diesel_runtime_maintenance': diesel_kWh * p['diesel_variable_om'],
        'grid_supply': grid_kWh * p['bulk_grid_supply'],
    }
    ledger = []
    def add(year, kind, name, amount, tax=0):
        ledger.append(dict(case=case, scenario=scenario, year=year, kind=kind, item=name,
                           cost_USD=amount, assumed_tax_USD=tax,
                           discounted_cost_USD=amount/(1+rate)**year))
    for name, value in initial.items():
        add(0, 'initial', name, value, value if name == 'assumed_tax' else 0)
    for year in range(1, T+1):
        for name, value in operating.items():
            add(year, 'operating', name, value)
        for item in items:
            if year < T and year % item['life'] == 0:
                repl = installed_package([item], p, initial=False)
                add(year, 'replacement', item['component'], sum(repl.values()), repl['assumed_tax'])
                if item['component'] != 'land_right':
                    add(year, 'retirement', item['component'], item['cost']*p['retirement_fraction'])
    for item in items:
        last_purchase = ((T-1)//item['life']) * item['life']
        remaining_fraction = max(0, (last_purchase+item['life']-T)/item['life'])
        # Optional remaining service value, net of purchase tax and initial development costs.
        pkg = installed_package([item], p, initial=False)
        remaining = (sum(pkg.values())-pkg['assumed_tax']) * remaining_fraction * p['salvage_fraction']
        add(T, 'residual_credit', item['component'], -remaining)
        if item['component'] != 'land_right':
            add(T, 'retirement', item['component'], item['cost']*p['retirement_fraction'])
    npc = sum(r['discounted_cost_USD'] for r in ledger)
    discounted_tax = sum(r['assumed_tax_USD']/(1+rate)**r['year'] for r in ledger)
    annualized = npc * annuity(rate, T)
    debt = capex*p['debt_share']; grant = capex*p['grant_share']; equity = capex-debt-grant
    annual_debt = debt * annuity(p['real_loan_rate'], p['loan_tenor_years'])
    summary = dict(case=case, scenario=scenario, label=design['label'],
                   evidence_status='illustrative_assumptions_not_procurement_quote', adequacy_status='not_checked',
                   price_basis='constant_2025_USD_assumptions', connections=design['connections'],
                   target_delivered_kWh_year=energy, initial_budget_USD=capex,
                   initial_USD_per_connection=capex/design['connections'],
                   annual_operating_USD=sum(operating.values()),
                   discounted_replacements_USD=sum(r['discounted_cost_USD'] for r in ledger if r['kind']=='replacement'),
                   lifecycle_NPC_USD=npc, NPC_excluding_assumed_tax_USD=npc-discounted_tax,
                   equivalent_annual_cost_USD=annualized,
                   conditional_USD_per_target_kWh=annualized/energy,
                   recovery_USD_per_collected_kWh=annualized/(energy*p['collection_fraction']),
                   real_discount_rate=rate, horizon_years=T, battery_life_years=p['battery_life_years'],
                   diesel_litres_year=diesel_kWh*p['diesel_specific_fuel'], grid_purchase_kWh_year=grid_kWh,
                   debt_USD=debt, grant_USD=grant, equity_USD=equity,
                   annual_debt_service_USD=annual_debt,
                   year1_operating_plus_debt_USD=sum(operating.values())+annual_debt)
    return dict(summary=summary, ledger=ledger, items=items, initial=initial, operating=operating,
                parameters=p, design=design)


def sensitivity_rows():
    rows = []
    for case in load_inputs()[2]:
        for param, values in [('real_discount_rate',[.06,.10,.18]), ('battery_life_years',[5,8,12]),
                              ('diesel_delivered_price',[1,1.5,3]), ('bulk_grid_supply',[.08,.15,.30])]:
            for value in values:
                s=evaluate(case,overrides={param:value})['summary']
                rows.append(dict(case=case,driver=param,value=value,unit=load_inputs()[1][param]['unit'],
                                 conditional_USD_per_target_kWh=s['conditional_USD_per_target_kWh'],
                                 initial_budget_USD=s['initial_budget_USD']))
    for km in [0,1,2,5,10,20,30]:
        s=evaluate('grid_extension',quantity_overrides={'mv_line':km})['summary']
        rows.append(dict(case='grid_extension',driver='new_MV_route_km',value=km,unit='route_km',
                         conditional_USD_per_target_kWh=s['conditional_USD_per_target_kWh'],
                         initial_budget_USD=s['initial_budget_USD']))
    return rows


def export_results():
    outputs=[evaluate(c,s) for s in SCENARIOS for c in load_inputs()[2]]
    write_csv(RESULTS/'cost_summary.csv',[o['summary'] for o in outputs])
    write_csv(RESULTS/'cashflow_ledger.csv',[r for o in outputs for r in o['ledger']])
    write_csv(RESULTS/'component_budgets.csv',[
        dict(case=o['summary']['case'],scenario=o['summary']['scenario'],**item)
        for o in outputs for item in o['items']])
    write_csv(RESULTS/'initial_cost_breakdown.csv',[
        dict(case=o['summary']['case'],scenario=o['summary']['scenario'],cost_item=k,cost_USD=v)
        for o in outputs for k,v in o['initial'].items()])
    write_csv(RESULTS/'sensitivity.csv',sensitivity_rows())
    manifest={p.name:hashlib.sha256(p.read_bytes().replace(b'\r\n',b'\n')).hexdigest()
              for p in sorted(DATA.iterdir()) if p.suffix in ('.csv','.json')}
    (RESULTS/'input_hashes.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    return outputs


if __name__ == '__main__':
    for output in export_results():
        s=output['summary']
        print(f"{s['case']:24} {s['scenario']:12} initial ${s['initial_budget_USD']:,.0f}; "
              f"NPC ${s['lifecycle_NPC_USD']:,.0f}; conditional ${s['conditional_USD_per_target_kWh']:.3f}/target kWh")
