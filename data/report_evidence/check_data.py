"""Check transcription structure, units, arithmetic and manifest integrity.

python data/report_evidence/check_data.py --refresh
python data/report_evidence/check_data.py
Checks cannot establish the underlying reports' factual accuracy.
"""
from pathlib import Path
import csv,hashlib,json,sys,math

ROOT=Path(__file__).resolve().parent
def read(name):
    with (ROOT/(name+'.csv')).open(encoding='utf-8',newline='') as f:return list(csv.DictReader(f))
def number(value):return float(value) if value!='' else None
def digest(path):return hashlib.sha256(path.read_bytes().replace(b'\r\n',b'\n')).hexdigest()

def main(refresh=False):
    sources={r['source_id']:r for r in read('source_register')}
    assert len(sources)==19
    tables={p.stem:read(p.stem) for p in sorted(ROOT.glob('*.csv')) if p.stem!='source_register'}
    ids=set()
    for name,rows in tables.items():
        for r in rows:
            assert r['record_id'] not in ids,(name,r['record_id'])
            ids.add(r['record_id'])
            assert r['source_id'] in sources
            assert 1<=int(r['pdf_page'])<=int(sources[r['source_id']]['pdf_pages'])
            assert all(r[x] for x in ['data_period','evidence_kind','reference'])
    assert sources['R01']['normalized_text_sha256']==sources['R07']['normalized_text_sha256']
    assert sources['R07']['duplicate_of']=='R01'
    for r in tables['market_prices_2025']:
        val=number(r['source_price_thousand_SDG'])
        if val is None:
            assert r['price_SDG']=='' and r['quote_status']=='missing_in_source'
        else:assert number(r['price_SDG'])==val*1000
        if r['product']=='solar_panel':
            assert r['derived_SDG_per_nominal_kWh']=='' and r['conversion_status']=='blocked_power_unit_ambiguity'
        elif val is not None:assert number(r['derived_SDG_per_nominal_kWh'])==val*100
    for r in tables['plant_status_2024']:
        if r['explicitly_reported_available_MW']:
            avail=number(r['explicitly_reported_available_MW']);cap=number(r['installed_capacity_MW'])
            assert 0<=avail<=cap
            assert math.isclose(number(r['derived_available_fraction']),avail/cap)
        else:assert r['derived_available_fraction']==''
    assert len(tables['plant_status_2024'])==20
    assert len([r for r in tables['plant_inventory_2019'] if r['category']=='pipeline'])==12
    assert len(tables['irrigation_model_results'])==24
    assert len({r['site_number'] for r in tables['irrigation_weather_sites']})==12
    for r in tables['irrigation_weather_sites']+tables['csp_candidate_zones']:
        assert -90<=number(r['latitude'])<=90 and -180<=number(r['longitude'])<=180
    findings=[]
    def check(name,actual,expected,tolerance=1e-8,comment=''):
        findings.append(dict(check=name,calculated=actual,source_or_expected=expected,
            difference=round(actual-expected,9),tolerance=tolerance,
            result='matches_within_tolerance' if abs(actual-expected)<=tolerance else 'source_discrepancy_retained',notes=comment))
    check('R17 Table6.2 listed shipment shares percent',sum(number(r['share_percent']) for r in tables['import_cost_shares_2025']),100,.11,'22 rounded percentages; not an equipment-price markup.')
    for col in ['installed_capacity_MW','available_capacity_MW','customers']:
        rows=tables['darfur_plants_2012']
        check('R02 Table2.6 '+col,sum(number(r[col]) for r in rows if r['is_total']=='False'),number(next(r for r in rows if r['is_total']=='True')[col]))
    for year in ['2015','2016','2017']:
        rows=[r for r in tables['sector_sales_customers'] if r['data_period']==year]
        for col in ['sales_MWh','customer_accounts']:
            check('R19 Annex3 '+year+' '+col,sum(number(r[col]) for r in rows if r['is_total']=='False'),number(next(r for r in rows if r['is_total']=='True')[col]),0,
                  'Preserve reported totals; small differences are not silently repaired.')
    check('R19 Table1.4 fuel total tonnes',sum(number(r['quantity_tonnes']) for r in tables['thermal_fuel_use_2017']),1699932)
    check('R19 Table1.4 fuel shares percent',sum(number(r['share_percent']) for r in tables['thermal_fuel_use_2017']),100,.05)
    check('R03 Equation2 annual PV yield kWh',365*2*.9*5,3523,0,'Published parameters do not reproduce the table yield.')
    check('R06 Table5 existing line length km',sum(number(r['value']) for r in tables['network_evidence'] if r['source_id']=='R06' and r['status'].startswith('existing')),10010.1,0,'Source total retained in check; detailed rows differ by10km.')
    for col in ['budget_2013_2016_million_USD','budget_2017_2019_million_USD','total_budget_million_USD']:
        expected={'budget_2013_2016_million_USD':507.1,'budget_2017_2019_million_USD':492.9,'total_budget_million_USD':1000}[col]
        check('R02 Annex8 '+col,sum(number(r[col]) for r in tables['darfur_investment_plan']),expected,.01)
    programme=[r for r in tables['programmes_and_projects'] if r['source_id']=='R15' and r['pdf_page']=='39']
    check('R15 programme budget million USD',sum(number(r['budget_million_USD']) for r in programme),250)
    check('R15 programme beneficiaries million',sum(number(r['beneficiaries_million']) for r in programme),6.05)
    rows=tables['generation_plan_comparison']; total=next(r for r in rows if r['is_total']=='True')
    for col in ['least_cost_capacity_MW','government_capacity_MW','least_cost_generation_GWh','government_generation_GWh']:
        check('R19 Table3.2 '+col,sum(number(r[col]) for r in rows if r['is_total']=='False'),number(total[col]),0,'Forecast outcomes, not observations; rounding differences retained.')
    manifest=dict(review_date='2026-10-17',source_files=19,distinct_documents=18,
        registered_pdf_pages=sum(int(r['pdf_pages']) for r in sources.values()),
        scope='Energy-relevant sections reviewed; prior forecasting and DRE extractions reused. Not every page of broad development reports transcribed.',
        data_tables=len(tables)-2, support_tables=['source_register','source_issues','data_source_leads'],
        records_excluding_source_register=sum(len(v) for v in tables.values()),
        checks=findings,validation='Schema and arithmetic checked; not independent validation of source facts or simulation outputs.',
        files={p.name:dict(rows=len(read(p.stem)),sha256_LF=digest(p),columns=list(read(p.stem)[0])) for p in sorted(ROOT.glob('*.csv'))})
    target=ROOT/'validation.json'
    if refresh:target.write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    else:
        saved=json.loads(target.read_text(encoding='utf-8'))
        assert saved==manifest,'Manifest drift; review changes and use --refresh.'
    print(f"Checked {len(manifest['files'])} CSVs and {len(ids)} unique records; {len(findings)} arithmetic comparisons.")
    for r in findings:
        if r['result']=='source_discrepancy_retained':print(r['check'],r['difference'])
    print('Source discrepancies are reported, not corrected or treated as test failures.')

if __name__=='__main__':main('--refresh' in sys.argv)
