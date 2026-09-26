"""Extract factual tables from Lahmeyer / MWRE report 260690 (18 Oct 2012).

Usage: python extract_data.py --pdf PATH [--cache PATH]
Requires pandas, pypdf and pdfplumber. The notebook needs only the resulting CSVs.
The supplied PDF is not redistributed. Raw table cells are deliberately unverified.
"""
from pathlib import Path
import argparse, calendar, csv, hashlib, json, re
import pandas as pd

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'data'
SOURCE_ID = 'MWRE_Lahmeyer_2012_260690'
SCENARIOS = ['Moderate', 'Base', 'High']
YEARS = list(range(2012, 2032))

def number(s):
    if s is None or str(s).strip().lower() in ('', 'na', 'n.a.', 'nogrid'):
        return float('nan')
    s = str(s).replace(',', '').replace('%', '').strip()
    if s.startswith('n '):  # p132: label overflows first numeric cell
        s = s[2:]
    return float(s)

def save(name, rows):
    df = rows if isinstance(rows, pd.DataFrame) else pd.DataFrame(rows)
    if 'source_id' not in df:
        df['source_id'] = SOURCE_ID
    df.to_csv(DATA / f'{name}.csv', index=False, encoding='utf-8-sig')
    return df

def extract(pdf, cache):
    from pypdf import PdfReader
    import pdfplumber
    cache.mkdir(parents=True, exist_ok=True)
    if not (cache / 'raw_tables.json').exists():
        reader = PdfReader(pdf)
        for i, p in enumerate(reader.pages, 1):
            (cache / f'page_{i:03}.txt').write_text(p.extract_text() or '', encoding='utf-8')
        tables = []
        with pdfplumber.open(pdf) as doc:
            for i, p in enumerate(doc.pages, 1):
                for j, cells in enumerate(p.extract_tables()):
                    tables.append(dict(pdf_page=i, table_index=j, cells=cells))
        (cache / 'raw_tables.json').write_text(json.dumps(tables), encoding='utf-8')
    tables = json.loads((cache / 'raw_tables.json').read_text(encoding='utf-8'))
    def table(page, index=0):
        return next(t['cells'] for t in tables if t['pdf_page'] == page and t['table_index'] == index)
    def page(n):
        return (cache / f'page_{n:03}.txt').read_text(encoding='utf-8')
    DATA.mkdir(parents=True, exist_ok=True)

    # All automatically detected tables remain available for further checking.
    raw = ROOT / 'raw_tables_unverified'
    raw.mkdir(exist_ok=True)
    inventory = []
    for t in tables:
        name = f"page_{t['pdf_page']:03}_table_{t['table_index'] + 1:02}.csv"
        with (raw / name).open('w', encoding='utf-8-sig', newline='') as f:
            csv.writer(f).writerows(t['cells'])
        inventory.append(dict(file=name, pdf_page=t['pdf_page'], rows=len(t['cells']),
                              columns=max(map(len, t['cells'])), status='automatic; not validated'))
    save('raw_table_inventory', inventory)

    # Complete national forecast: metric mapping avoids repeated/blank PDF labels.
    names = {
        3:'load_factor_pct',4:'peak_mw',5:'peak_growth_mw',6:'peak_growth_pct',
        7:'sent_out_gwh',8:'sent_out_growth_gwh',9:'sent_out_growth_pct',
        10:'transmission_loss_pct',11:'transmission_loss_gwh',12:'distribution_loss_pct',13:'distribution_loss_gwh',
        14:'connections_total',15:'connections_growth_pct',16:'connections_domestic',17:'connections_domestic_growth_pct',
        18:'connections_domestic_added',19:'connections_domestic_share_pct',20:'electrification_rounded_pct',
        21:'connections_industrial',22:'connections_industrial_growth_pct',23:'connections_industrial_share_pct',
        24:'connections_commercial',25:'connections_commercial_growth_pct',26:'connections_commercial_share_pct',
        27:'connections_agricultural',28:'connections_agricultural_growth_pct',29:'connections_agricultural_share_pct',
        30:'connections_governmental',31:'connections_governmental_growth_pct',32:'connections_governmental_share_pct',
        33:'billed_gwh',34:'billed_growth_pct',35:'domestic_gwh',36:'domestic_growth_pct',37:'domestic_share_pct',
        38:'industrial_gwh',39:'industrial_growth_pct',40:'industrial_share_pct',41:'commercial_gwh',
        42:'commercial_growth_pct',43:'commercial_share_pct',44:'agricultural_gwh',45:'agricultural_growth_pct',
        46:'agricultural_share_pct',47:'governmental_gwh',48:'governmental_growth_pct',49:'governmental_share_pct',
        50:'population_million',51:'population_growth_pct',52:'urban_population_million',53:'urban_population_share_pct',
        54:'rural_population_million',55:'households_million',56:'connected_households_million',57:'grid_access_pct',
        59:'states_connected',60:'states_connected_pct',61:'localities_connected',62:'localities_connected_pct'}
    rows = []
    for scenario, p in zip(SCENARIOS, [126,128,130]):
        t = table(p)
        assert [int(v) for v in t[1][4:]] == YEARS
        for i, metric in names.items():
            for year, rawvalue in zip(YEARS, t[i][4:]):
                rows.append(dict(scenario=scenario, year=year, metric=metric, value=number(rawvalue),
                                 raw_value=rawvalue, source_unit=t[i][2], pdf_page=p, table_row_0based=i,
                                 note='Printed unit # interpreted as million from population identity' if i==54 else ''))
    national = save('national_forecast_long', rows)
    wide = national.pivot(index=['scenario','year','pdf_page'], columns='metric', values='value').reset_index()
    save('national_forecast', wide)

    rows, access = [], []
    for scenario, p in zip(SCENARIOS, [127,129,131]):
        t = table(p)
        for k in range(17):
            i = 2 + 4*k
            state = t[i][0] if k < 15 else ('Sudan West aggregate' if k==15 else 'Sudan total')
            for j, year in enumerate(YEARS, 4):
                rows.append(dict(scenario=scenario, state=state, geography='historical 15-state system',
                                 aggregate=k>=15, year=year, billed_gwh=number(t[i][j]),
                                 growth_pct=number(t[i+1][j]), share_pct=number(t[i+2][j]),
                                 load_at_system_peak_mw=number(t[i+3][j]), pdf_page=p))
        for k in range(16):
            i = 73+3*k
            state = t[i][1] if k<15 else 'Sudan total'
            for j, year in enumerate(YEARS,4):
                access.append(dict(scenario=scenario, state=state, aggregate=k==15, year=year,
                                   overall_pct=number(t[i][j]), grid_pct=number(t[i+1][j]),
                                   offgrid_target_pct=number(t[i+2][j]), pdf_page=p))
    save('state_forecast', rows)
    save('state_access_forecast', access)

    rows = []
    t = table(119)
    for row in t[2:]:
        for k, sector in enumerate(['domestic','industrial','commercial','agricultural','governmental']):
            for j, year in enumerate(range(2011,2005,-1)):
                rows.append(dict(state=row[0], aggregate=row[0].upper().startswith('TOTAL'), sector=sector, year=year,
                                 consumption_gwh=number(row[1+6*k+j]), pdf_page=119))
    save('historical_consumption', rows)

    cols = ['locality_id','locality','state','area_km2','area_share_pct','population_2008','urban_pct',
            'household_size','households','density_per_km2','national_grid_2012','isolated_grids',
            'supply_coverage_km2','supply_coverage_pct','distance_to_national_grid_km','transmission_project_status_2012']
    rows = []
    for p in [123,124]:
        for row in table(p):
            if re.fullmatch(r'L\d+', row[0] or ''):
                d = dict(zip(cols,row)); d['pdf_page']=p
                for c in cols:
                    if c not in ['locality_id','locality','state','national_grid_2012','transmission_project_status_2012']:
                        d[c] = number(d[c])
                d['distance_note'] = ('Zero with no grid: no route identified; not distance zero to a live line'
                                      if d['national_grid_2012']=='no' and d['distance_to_national_grid_km']==0 else '')
                rows.append(d)
    localities = save('localities_2008_2012', rows)
    assert len(localities)==131 and localities.locality_id.nunique()==131

    rows = []
    for row in table(114)[1:]:
        if not row[0] or 'growth' in row[0].lower(): continue
        for year, value in zip(range(2009,2032),row[1:]):
            rows.append(dict(state=row[0], year=year, population_million=number(value), pdf_page=114,
                             observation_type='CBS projection as reproduced in 2012 report'))
    save('population_projection', rows)
    rows = []
    census_cols = ['population','population_share_pct','households','household_size','urban_pct','rural_pct',
                  'nomadic_pct','area_km2','area_share_pct','area_close_to_grid_km2','area_close_to_grid_pct','density_per_km2']
    for line in page(115).splitlines():
        m = re.match(r'^(.+?)\s+(\d[\d.]*\s+\d+%\s+.+)$',line)
        if m:
            vals=m[2].split()
            if len(vals)==12:
                vals=[float(x.replace('.','').replace(',','.').replace('%','')) for x in vals]
                rows.append(dict(state=m[1], year=2008, **dict(zip(census_cols,vals)),pdf_page=115))
    assert len(rows)==16
    save('state_census_2008',rows)
    rows=[]
    for ti in [0,1]:
        for row in table(117,ti)[1:]:
            for y,v in zip(range(2000,2012),row[-12:]):
                rows.append(dict(series=row[0],year=y,value=number(v),pdf_page=117,
                                 unit='percent' if ti==1 or 'Growth' in row[0] else 'million SDG at 1981/82 prices (printed unit)',
                                 table='growth_comparison' if ti else 'sector_gdp',primary_estimate=y>=2010))
    save('historical_gdp', rows)

    ids = 'KN_1-ST KN_2-ST KN_3-4-ST KN_5-6-ST KN_0-GT G1_B1-2-CCGT2+1 G2_B1-2-CCGT2+1 G4_U1-2-ST ReS-ST AlF-ST Kos-ST M-HP Ros-HP Sen-HP Jeb-HP KhE-HP UpA-HP ResD-HP SenU-HP'.split()
    plants = pd.DataFrame({'plant_id':ids})
    plants['name']=['Khartoum North 1','Khartoum North 2','Khartoum North 3+4','Khartoum North 5+6',
                    'Khartoum North GT','Garri 1 blocks 1+2','Garri 2 blocks 1+2','Garri 4 units 1+2',
                    'Red Sea','Al Fula','Kosti','Merowe','Roseires','Sennar','Jebel Aulia','Khashm El Girba',
                    'Upper Atbara','Roseires dam heightening','Sennar upgrading']
    plants['status_in_2012']=['exists']*8+['committed']*3+['exists']*5+['committed']*3
    plants['technology']=['ST']*4+['GT','CCGT','CCGT','ST','ST','ST','ST']+['hydro']*8
    plants['primary_fuel']=['HCGO','HCGO','HFO','HFO','Gasoil','Gasoil','Gasoil','Sponge Coke','Coal','Gas Blend (Neem)',
                            'Crude']+['Hydro']*8
    plants['substation']=['KHN']*5+['GAR']*3+['POR1','FUL','RBK','MWP','ROS','SMP','JAS','GRB','not known','ROS','SMP']
    plants['state']=['Khartoum']*8+['Red Sea','South Kordofan','White Nile','North','Blue Nile','Sinnar',
                                  'White Nile/Khartoum','Al Gadarif','Al Gadarif','Blue Nile','Sinnar']
    numeric_lines = {
        'latitude':'Latitude N ', 'longitude':'Longitude E ',
        'gross_capacity_mw':'Plant Capacity Installed (Gross) MW ',
        'net_max_capacity_mw':'Plant Max. Capacity Available (Net) MW ',
        'self_consumption_pct':'Self-Consumption % ',
        'fixed_om_usd_per_kw_year':'Costs O&M Fixed USD/kW/year ',
        'variable_om_usd_per_mwh':'O&M Variable USD/MWh ',
        'generation_average_row_gwh':'Generation (net) average (historic) GWh/a ',
        'generation_planned_average_gwh':'average (planned) ',
        'generation_firm_gwh':'firm 90% (hydro) / effective availability (thermal) GWh/a ',
        'availability_pct':'Effective Availability (EA) % '}
    for col,prefix in numeric_lines.items():
        line=next(x for x in page(120).splitlines() if prefix in x)
        vals=line.split(prefix,1)[1].split()
        assert len(vals)==19, (col,vals)
        plants[col]=[number(v) for v in vals]
    for col,prefix in [('efficiency_pct','Max. Efficiency % '),('forced_outage_pct','Foreced Outage Rate (FOR) % '),
                       ('planned_outage_days','Planned Outage Rate (POR) days/year ')]:
        line=next(x for x in page(120).splitlines() if prefix in x)
        vals=line.split(prefix,1)[1].split()[:11]
        plants[col]=[number(v) for v in vals]+[float('nan')]*8
    plants['replacement_of']=['']*17+['Ros-HP','Sen-HP']
    plants['average_row_classification']=plants.status_in_2012.map({
        'exists':'Historic average as reported',
        'committed':'Planning value in mixed/merged average row; not observed generation'})
    plants['pdf_page']=120
    plants['note']='2012 technical record, not an observed 2022 asset register; costs have unverified price base'
    save('plant_characteristics', plants)

    # Archive aligned cell words for less regular plant fields. This preserves ambiguities,
    # including the merged 2011 value for Khartoum North 1 and 2, without shifting columns.
    with pdfplumber.open(pdf) as doc:
        words=doc.pages[119].extract_words(x_tolerance=1,y_tolerance=1)
        centers=[(w['x0']+w['x1'])/2 for w in words if abs(w['top']-103.35516)<0.6 and w['text'].isdigit()]
        assert len(centers)==19
        bounds=[centers[0]-(centers[1]-centers[0])/2]+[(a+b)/2 for a,b in zip(centers,centers[1:])]+[centers[-1]+20]
        out=[]
        for top in sorted(set(round(w['top'],1) for w in words if 110<w['top']<550)):
            ww=[w for w in words if round(w['top'],1)==top]
            labels=' '.join(w['text'] for w in ww if w['x1']<bounds[0])
            cells=[' '.join(w['text'] for w in ww if bounds[i]<=(w['x0']+w['x1'])/2<bounds[i+1]) for i in range(19)]
            out.append(dict(pdf_page=120,y_points=top,label=labels,**dict(zip(ids,cells))))
        save('plant_geometric_rows_unverified',out)
        # Numerical historical rows have one aligned cell per plant; preserve blanks.
        history=[]
        for basis,tops in [('net',[335.8,343.2,350.8,358.2,365.8]),
                           ('gross',[425.8,433.2,440.8,448.2,455.8])]:
            for year,top in zip(range(2011,2006,-1),tops):
                ww=[w for w in words if abs(w['top']-top)<0.6]
                for i,pid in enumerate(ids):
                    v=' '.join(w['text'] for w in ww if bounds[i]<=(w['x0']+w['x1'])/2<bounds[i+1])
                    history.append(dict(plant_id=pid,year=year,basis=basis,generation_gwh=number(v),
                                        raw_value=v,pdf_page=120,note='Blank retained; no interpolation or allocation'))
        save('plant_historical_generation',history)
        for col,top in [('first_operation_year_as_reported',470.7),('last_operation_year_as_reported',478.2)]:
            ww=[w for w in words if abs(w['top']-top)<0.6]
            plants[col]=[' '.join(w['text'] for w in ww if bounds[i]<=(w['x0']+w['x1'])/2<bounds[i+1]) for i in range(19)]
        save('plant_characteristics',plants)

    hydro, heat = [], []
    metric=None
    for line in page(121).splitlines():
        if 'At ' in line and '% load kJ/kWh' in line:
            load=int(re.search(r'At (\d+)%',line)[1])
            vals=line.split('kJ/kWh',1)[1].split()
            assert len(vals)==19
            for pid,v in zip(ids[:11],vals[:11]):
                heat.append(dict(plant_id=pid,load_pct=load,heat_rate_kj_per_kwh=number(v),pdf_page=121))
        for label,key in [('Minimum Capacity (hydro only)','minimum_mw'),('Available (dependable) capacity (hydro)','dependable_mw'),
                          ('Firm power (hydro only)','firm_mw'),('Mean generation (hydro only)','mean_generation_mwh_per_day')]:
            if label in line: metric=key
        if metric:
            month=next((i for i in range(1,13) if calendar.month_name[i] in line),None)
            if month:
                vals=line.split()[-8:]
                for pid,v in zip(ids[11:],vals):
                    hydro.append(dict(plant_id=pid,month=month,metric=metric,value=number(v),pdf_page=121))
    assert len(hydro)==384 and len(heat)==99
    h=save('hydro_monthly_long',hydro)
    save('hydro_monthly',h.pivot(index=['plant_id','month','pdf_page'],columns='metric',values='value').reset_index())
    save('thermal_heat_rates',heat)

    t=table(132);rows=[]
    for si,scenario in enumerate(SCENARIOS):
        for j,year in enumerate(YEARS,5):
            d=dict(scenario=scenario,year=year,pdf_page=132)
            for key,ri in [('capacity_mw',2),('reserve_mw',4+si),('peak_mw',8+si),('required_mw',11+si),
                           ('power_gap_mw',15+si),('firm_energy_gwh',19),('energy_demand_gwh',21+si),('energy_gap_gwh',25+si)]:
                d[key]=number(t[ri][j])
            rows.append(d)
    save('annual_supply_balance',rows)
    t=table(133);rows=[]
    for start in [0,25,50,75]:
        for si,scenario in enumerate(SCENARIOS):
            for j in range(2,62):
                d=dict(scenario=scenario,year=int(t[start][j]),month=(j-2)%12+1,pdf_page=133)
                for key,ri in [('capacity_mw',2),('peak_mw',4+si),('required_mw',7+si),('power_gap_mw',11+si),
                               ('firm_energy_gwh',15),('energy_demand_gwh',17+si),('energy_gap_gwh',21+si)]:
                    d[key]=number(t[start+ri][j])
                d['capacity_missing_in_pdf']=pd.isna(d['capacity_mw'])
                rows.append(d)
    save('monthly_supply_balance',rows)

    rows=[]
    for line in page(56).splitlines():
        m=re.fullmatch(r'(\d+) kV (\d+) (\d+)',line)
        if m: rows.append(dict(voltage_kv=int(m[1]),number_of_lines=int(m[2]),total_length_km=int(m[3]),pdf_page=56))
    save('transmission_summary_2012',rows)
    rows=[]; state=None
    for line in page(62).splitlines():
        # Rows are single physical lines in PDF text, including the section state once.
        m=re.match(r'^(.*?)\s+(\d+)\s+(110|220)$',line)
        if not m: continue
        name=m[1]
        sm=re.match(r'^\d+ (Al Gezira|Red Sea|Blue Nile|North Kordufan|South Kordufan|North Darfur|West Darfur|South Darfur) (.+)$',name)
        if sm: state,name=sm[1],sm[2]
        route=re.sub(r'\s*[\ufffd\u2013]\s*',' - ',name)
        rows.append(dict(state=state,route=route,length_km=int(m[2]),voltage_kv=int(m[3]),
                         status_in_2012='planned, not evidence of construction',thermal_rating_mw=float('nan'),pdf_page=62))
    assert len(rows)==37, len(rows)
    save('planned_transmission_routes_2012',rows)

    metadata=dict(title='Long and Medium Term Power System Plans Sudan: Demand Forecast Report, FINAL Revision',
                  report_number='260690',report_date='2012-10-18',author='Lahmeyer International',
                  client='Ministry of Water Resources and Electricity, Republic of Sudan',pdf_pages=139,
                  source_id=SOURCE_ID,source_filename=pdf.name,sha256=hashlib.sha256(pdf.read_bytes()).hexdigest(),
                  extracted_on='2026-09-26',page_numbering='Physical PDF page, starting at 1; printed numbering restarts',
                  classification='Mixed historical observations, assumptions and forecasts; not observed 2022 data',
                  original_workbook_embedded=bool(list(PdfReader(pdf).attachments)),
                  raw_table_count=len(tables),geography='Historical 15 states and 131 localities; not modern 18-state boundaries')
    (ROOT/'source_metadata.json').write_text(json.dumps(metadata,indent=2),encoding='utf-8')
    print(json.dumps(dict(normalized_csv_files=len(list(DATA.glob('*.csv'))),raw_tables=len(tables),localities=len(localities)),indent=2))

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--pdf',type=Path,required=True)
    ap.add_argument('--cache',type=Path,default=ROOT/'.extraction_cache')
    args=ap.parse_args();extract(args.pdf,args.cache)
