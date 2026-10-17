"""Rebuild curated factual tables transcribed from the supplied PDF collection.

This is a reviewed transcription, not a general-purpose PDF parser. Source files
and full-text working extracts are deliberately not distributed. See REVIEW.md.
Python standard library only; no model inputs are overwritten.
"""
from pathlib import Path
from collections import defaultdict
import csv, hashlib, json

ROOT = Path(__file__).resolve().parent
TABLES = defaultdict(list)

def add(table, source, page, reference, period, kind, notes='', **data):
    rows = TABLES[table]
    row = dict(record_id=f'{table}_{len(rows)+1:03d}', source_id=source,
               pdf_page=page, reference=reference, data_period=period,
               evidence_kind=kind, **data, notes=notes)
    rows.append(row)

def param(source, page, reference, period, tech, name, value, unit, notes='', price_year=''):
    add('study_parameters',source,page,reference,period,'study_assumption',notes,
        technology=tech,parameter=name,value=value,unit=unit,price_year=price_year,
        model_use='sensitivity_or_replication_only')

def indicator(source,page,ref,period,metric,value,unit,notes='',kind='reported_statistic',geography='Sudan'):
    add('system_indicators',source,page,ref,period,kind,notes,geography=geography,
        metric=metric,value=value,unit=unit)

# R17: table 6.3. Preserve every geographical/date cell, including missing quotes.
cities=['Atbara','Port Sudan','Dongola','Khartoum']
prices=[('solar_panel','2025-09-18',[218,218,218,218]),
        ('solar_panel','2025-09-28',[245,219,None,255]),
        ('solar_panel','2025-10-16',[225,None,230,252]),
        ('lithium_ion_battery','2025-09-18',[5400,5094,None,5094]),
        ('lithium_ion_battery','2025-09-28',[5300,5227,None,5227]),
        ('lithium_ion_battery','2025-10-16',[5000,5300,None,5300])]
for product,date,vals in prices:
    for city,value in zip(cities,vals):
        battery=product=='lithium_ion_battery'
        add('market_prices_2025','R17',29,'Table 6.3; printed p27',date,'reported_market_quote',
            'Equipment quote, not installed system cost. Exchange rate and installation scope absent. '+
            ('Nominal energy; usable capacity, power rating, chemistry and warranty absent.' if battery else
             'Source says 590 kW, min. 10 pallets. Suspected unit error; no USD/kW or SDG/kW conversion.'),
            city=city,product=product,specification_as_printed='10 kWh' if battery else '590 kW; min. 10 pallets',
            source_price_thousand_SDG=value,price_SDG=None if value is None else value*1000,
            nominal_energy_kWh=10 if battery else None,
            derived_SDG_per_nominal_kWh=value*100 if battery and value is not None else None,
            quote_status='missing_in_source' if value is None else 'reported',
            conversion_status='nominal_energy_conversion_only' if battery else 'blocked_power_unit_ambiguity')

fees=[('SSMO Certificate',.48),('Ministry of Trade',.36),('IM Form',13.07),('Delivery Order',9.24),
 ('Port workers',.89),('SSMO Fees',2.19),('Customs fees',.02),('SPC',15.08),
 ('Port to Free Zone transport',4.42),('Free Zone to warehouse transport',1.77),
 ('Crane loading and unloading',2.41),('Offloading at Free Zone',2.01),('Offloading at warehouse',.64),
 ('Free zone truck entry and exit',1.78),('Clearance commission',3.21),('Demurrage and other local costs',16.96),
 ('Four truck rentals: Dongola Omdurman Atbara Medani',18.65),('Business Profit Tax',4.82),
 ('Road fees in Port Sudan',.80),('Road fees to state warehouses',.38),('Fees for Business Profit Tax',.48),
 ('SSMO Certificate',.32)]
for number,(item,share) in enumerate(fees,1):
    add('import_cost_shares_2025','R17',29,'Table 6.2; printed p27','2025-09','reported_shipment_cost_share',
        'One five-container shipment. Absolute cost and quantities withheld; shares are of the listed cost basket, not a percentage markup on panel purchase cost.',
        item_number=number,item=item,share_percent=share)

# Additional interview quotations are deliberately separate from dated city prices.
for item,period,value,unit,notes in [
 ('550 W panel','pre-war',75000,'SDG/item','Approximate retrospective interview quote; exact date and location absent.'),
 ('550 W panel','2025',330000,'SDG/item','Approximate interview quote; exact date and location absent.'),
 ('200 Ah battery','pre-war',250000,'SDG/item','Voltage and chemistry absent; cannot convert Ah to kWh.'),
 ('200 Ah battery','2025',900000,'SDG/item','Voltage and chemistry absent; cannot convert Ah to kWh.'),
 ('3 kW inverter','pre-war',120000,'SDG/item','Brand, system scope and exact date absent.'),
 ('3 kW inverter','2025',600000,'SDG/item','Brand, system scope and exact date absent.'),
 ('580 W panel minimum quote','2025 interview context',300000,'SDG/item','Range lower endpoint; not a representative price distribution.'),
 ('580 W panel maximum quote','2025 interview context',350000,'SDG/item','Range upper endpoint; exact observation date absent.'),
 ('Cable','2025 interview context',1000,'SDG/m','Approximate; cross-section and conductor absent; not distribution line cost.')]:
    add('interview_prices','R17',31,'Section 6.3; printed p29',period,'interview_estimate',notes,item=item,value=value,unit=unit)

# Dated indicative fuel prices; blank means unavailable/not reported, never free fuel.
for city,diesel,gas,availability in [
 ('Port Sudan',2711,2831,'available; no black market reported'),
 ('Shandi',2800,3111,'no black market reported'),
 ('Sinnar',None,None,'unavailable in stations and black market'),
 ('Kosty',8333,15555,'black market only; stations out of service'),
 ('Omdurman',3050,None,'gasoline price not reported'),
 ('Darfur region; Khartoum city; Kordofan region',None,None,'black market dependence; no prices given')]:
    for fuel,value in [('diesel',diesel),('gasoline',gas)]:
        add('fuel_prices_2024','R12',9,'Table 1; qualification on PDF p10','2024-08','indicative_anecdotal_price',
            'Source based on anecdotal interviews and online resources. No exchange-rate conversion or current-price claim.',
            location=city,fuel=fuel,price_SDG_per_litre=value,availability=availability)

# Existing and pipeline assets in the 2019 diagnostic, exactly separated.
fleet='''Merowe|2009|Hydro||1250
Kosti|2008|Steam turbine|Crude oil|500
Garri 1 and 2|2002|Combined cycle gas turbine|LDO/HCGO|469
Garri 4|2006|Steam turbine|SC|110
Mahmoud Sharif steam|1985|Steam turbine|HFO/HCGO|380
Mahmoud Sharif gas|2016|Gas turbine|LDO/HCGO|150
Roseires|1971|Hydro||280
Port Sudan diesel|1983|Diesel engine|DO/LDO|40
Jabal Awlia|2005|Hydro||30.4
Sinnar|1962|Hydro||15
Khashm El Girba|1965|Hydro||17.8
E Obied|1987|Diesel engine|DO/LDO|12.7
Seitat and Upper Atbara|2018|Hydro||320
Al-Fasir|2002|Diesel engine|LDO/DO|31
Nyala|1985|Diesel engine|HFO/DO/LDO|32
El-Ginena|1989|Diesel engine|DO/LDO|10
Kadogli|2004|Diesel engine|DP/LDO|8
El-Nohod|2004|Diesel engine|DP/LDO|8.4
El-Diain|2004|Diesel engine|DO/LDO|7.5
Zalingei|2015|Diesel engine|LDO|2.6
Garri 3|2019|Gas turbine|HFO|561
Port Sudan new|2019|Gas turbine|HFO|376
Al-Fasir solar|2019|PV hybrid with diesel||5
El Dein solar|2019|PV hybrid with diesel||5
Darfur rental|2019|Diesel engine|HFO + LDO|150
Garri 3 upgrade|2021|Combined cycle gas turbine|Exhaust flue gas|240
Port Sudan upgrade|2021|Combined cycle gas turbine|Exhaust flue gas|1175
Al-Bagir|2021|Combined cycle gas turbine|HFO|350
Al-Fulah|2021|Gas turbine|Gas|450
Dongola|2021|Wind||1
Red Sea|2022|Steam turbine|Coal|1000
Elshaheed|2022|Gas turbine|HFO and LDO|350'''
for i,line in enumerate(fleet.splitlines()):
    name,year,tech,fuel,cap=line.split('|')
    add('plant_inventory_2019','R19',49,'Annex 1','2019 report; mixed asset vintages','reported_inventory' if i<20 else 'planned_asset',
        'Year preserved as printed, not verified commissioning year. DO is described as 70% LDO + 30% HFO. No coordinates. '+
        ('Pipeline entry is not evidence of commissioning.' if i>=20 else 'Capacity basis not reconciled with the 2022 net-capacity baseline.'),
        asset_name=name,year_as_printed=int(year),technology=tech,fuel_as_printed=fuel,installed_capacity_MW=float(cap),
        category='on_grid' if i<13 else 'isolated_grid' if i<20 else 'pipeline')

statuses=[
 ('Merowe',2009,'Hydro','',1250,'North','available',None,'Available; no numeric available MW explicitly reported.'),
 ('Kosti',2008,'Steam turbine','Crude oil',500,'South','fuel_limited',125,'One generator operating; fuel shortage.'),
 ('Garri 1 and 2',2008,'Combined cycle gas turbine','LDO/HCGO',469,'North','shut_down',None,'Fuel and staff unavailable.'),
 ('Garri 4',2006,'Steam turbine','Coal SC',110,'North','shut_down',None,'Staff unavailable; SC label preserved.'),
 ('Mahmoud Sharif steam',1985,'Steam turbine','HFO/HCGO',380,'North','shut_down',None,'Fuel and staff unavailable.'),
 ('Mahmoud Sharif gas',2016,'Gas turbine','LDO/HCGO',150,'North','shut_down',None,'Fuel and staff unavailable.'),
 ('Roseires',1971,'Hydro','',280,'South','available',None,'No numeric availability stated.'),
 ('Port Sudan Turkish barge',None,'Thermal','',35,'North','payment_interrupted',35,'Payment-related interruptions; wording in source contains a typo.'),
 ('Jabal Awlia',2005,'Hydro','',30.4,'South','unavailable_maintenance',None,'Major maintenance required.'),
 ('Sinnar',1962,'Hydro','',15,'South','partially_available',7.5,'One generator; major maintenance required.'),
 ('Khashm El Girba',1965,'Hydro','',17.8,'','partially_available',7.8,'Major maintenance required; grid blank in source.'),
 ('E Obied',1987,'Diesel engine','DO/LDO',12.7,'South','out_of_service',None,'Cause not specified in Annex.'),
 ('Seitat and Upper Atbara',2018,'Hydro','',320,'North','available',None,'Annex says North but PDF p7 narrative says Southern Grid; unresolved.'),
 ('Al-Fasir',2002,'Diesel engine','HFO/DO/LDO',31,'isolated','completely_damaged',None,'Report description; repair cost and repairability not established.'),
 ('Nyala',1985,'Diesel engine','DO/LDO',10,'isolated','partially_available',None,'Frequent fuel interruption; capacity differs from 2019 Nyala 32 MW.'),
 ('El-Ginena',1989,'Diesel engine','DO/LDO',10,'isolated','partially_available',None,'Frequent fuel interruption.'),
 ('Kadogli',2004,'Diesel engine','DP/LDO',8,'isolated','partially_available',None,'Frequent fuel interruption.'),
 ('El-Nohod',2004,'Diesel engine','DP/LDO',8.4,'isolated','partially_available',None,'Frequent fuel interruption.'),
 ('El-Diain',2004,'Diesel engine','DP/LDO',7.5,'isolated','partially_available',None,'Frequent fuel interruption.'),
 ('Zalingei',2015,'Diesel engine','LDO',2.6,'isolated','partially_available',None,'Frequent fuel interruption.')]
for i,(name,year,tech,fuel,cap,grid,status,available,note) in enumerate(statuses):
    add('plant_status_2024','R12',11 if i<8 else 12 if i<13 else 13,'Annex 1' if i<13 else 'Annex 2',
        '2024-08','reported_operational_status',note+' No annual availability or destruction percentage inferred.',
        asset_name=name,year_as_printed=year,technology=tech,fuel_as_printed=fuel,
        installed_capacity_MW=cap,grid_as_printed=grid,status_category=status,
        explicitly_reported_available_MW=available,
        derived_available_fraction=available/cap if available is not None else None)

for name,cap,avail,customers in [('El Fashir',22.48,15.4,18500),('Nyala',29.19,17.6,21915),
 ('El Daein',7.9,1.5,1600),('El Geneina',10.365,7,7500),('Zalingei',3.2,1,890),('Total',73.135,42.5,50405)]:
    add('darfur_plants_2012','R02',31,'Table 2.6; printed p18; DJAM 2012 Power Report','2012','reported_inventory',
        'Historical availability, not war damage. Zalingei narrative on same page instead says 0.8 MW.',
        plant=name,installed_capacity_MW=cap,available_capacity_MW=avail,customers=customers,is_total=name=='Total')

sales=[('Residential',[5973123,6693310,7352511],[2020878,2096756,2218516]),
 ('Industrial',[1512258,1794317,2003377],[1852,2006,2216]),
 ('Commercial',[1378184,1473870,1568314],[217565,227591,235989]),
 ('Agricultural',[650664,718924,873881],[17772,19422,21486]),
 ('Government',[1034352,1087877,1163088],[44734,46025,50256]),
 ('Company facilities / internal consumption',[32033,27232,25445],[257,265,266]),
 ('Total',[10580614,11795530,12986616],[2303058,2392065,2528729])]
for sector,energies,customers in sales:
    for year,e,n in zip([2015,2016,2017],energies,customers):
        add('sector_sales_customers','R19',51,'Annex 3',str(year),'reported_utility_statistics',
            'Served sales and customer accounts; not total latent demand or population. Rounded source totals may differ from sums.',
            sector=sector,sales_MWh=e,customer_accounts=n,is_total=sector=='Total',
            derived_kWh_per_account_month=e*1000/n/12)

tariffs=[('Domestic','1-200',.15,.003),('Domestic','201-400',.26,.005),('Domestic','401-600',.32,.007),
 ('Domestic','601-800',.52,.011),('Domestic','801-1500',.85,.018),('Domestic','above 1500',1.60,.034),
 ('Agriculture','up to 50 HP; national research and training',.16,.003),('Agriculture','above 50 HP',1.60,.034),
 ('Industry','medicine',.18,.004),('Industry','other',1.60,.034),('Cold stores and ice','1-400',.34,.007),
 ('Cold stores and ice','above 400',.85,.018),('Commercial','0-200',.34,.007),('Commercial','201-300',.85,.018),
 ('Commercial','301-400',1,.021),('Commercial','above 400',1.6,.034),('Service','water works and holy places',.33,.007),
 ('Schools','government schools',.33,.007),('Schools','private student hostels',.33,.007),
 ('Private hospitals and universities','all',.75,.016),('Government','departments',.70,.016),
 ('Tourism','hotels',.85,.018),('Communications embassies organizations','all',1.60,.034)]
for sector,tranche,sdg,usd in tariffs:
    add('tariffs_2018','R19',50,'Annex 2','2018','reported_tariff',
        'Historical subsidized customer tariff, not economic generation cost. USD column preserved including rounding inconsistencies.',
        sector=sector,tranche_as_printed=tranche,SDG_per_kWh=sdg,USD_per_kWh_as_printed=usd,source_exchange_rate_SDG_per_USD=47.6)

# Historical infrastructure aggregates do not define individual line topology or ratings.
for voltage,length,status in [(500,965.5,'existing North'),(500,4676,'planned 2016-2031'),
 (220,7692.9,'existing East and West'),(220,4445,'planned 2016-2031'),(220,1990,'planned 2016-2020'),
 (110,1128.7,'existing East'),(66,233,'existing East and West')]:
    add('network_evidence','R06',12,'Table 5; printed p11','2015 baseline','reported_network_aggregate',
        'Secondary citation to source [13]. Planned periods overlap; never sum planned categories or infer line MW rating from kV.',
        geography='Sudan',metric='line_length',value=length,unit='km',voltage_kV=voltage,status=status)
for loc,metric,value,unit,status in [('Ethiopia','firm_PPA_capacity',100,'MW','historical contract'),
 ('Ethiopia','PPA_energy_price',.05,'USD/kWh','historical contract'),('Ethiopia','interconnection_capacity',200,'MW','operational in report'),
 ('Egypt','interconnection_capacity',300,'MW','completion/under-construction wording differs across report')]:
    add('network_evidence','R19',21,'Paragraph 33; see also p40','2019 report','reported_interconnection',
        'Keep PPA quantity separate from physical capability and actual imports; no 2022 or current verification.',
        geography=loc,metric=metric,value=value,unit=unit,voltage_kV=220 if loc=='Ethiopia' else None,status=status)
for loc,metric,value,period in [('Ethiopia','reported_power_trade',150,'pre-conflict'),('Ethiopia','reported_power_trade',50,'post-conflict August 2024 context'),
 ('Egypt','average_import',60,'August 2024 context'),('Egypt','line_capacity_before_upgrade',80,'pre-upgrade'),('Egypt','announced_line_capacity_after_STATCOM',300,'announced upgrade 2024')]:
    add('network_evidence','R12',7,'Paragraph 7','2024 report; '+period,'reported_interconnection',
        'MW, not annual energy. Announced capability is not guaranteed firm supply.',geography=loc,metric=metric,value=value,unit='MW',voltage_kV=None,status=period)

# Context indicators with their time and denominator preserved.
for metric,val,unit in [('transmission_loss',5.4,'percent'),('distribution_loss',15.1,'percent'),
 ('collection_rate',93,'percent'),('SAIDI',9.18,'hours/customer/year'),('SAIFI',10.14,'interruptions/customer/year'),
 ('cost_of_service_scorecard',.20,'USD/kWh'),('average_tariff',.015,'USD/kWh')]:
    indicator('R19',20,'Table 1.5','2017',metric,val,unit,'Loss denominators differ; do not add rates. SAIDI/SAIFI do not quantify all scheduled load shedding; cost differs from p30 estimate.')
for year,val in [(2013,13.1),(2014,12.8),(2015,9),(2016,11.5),(2017,10.1)]:
    indicator('R19',17,'Table 1.2',str(year),'electricity_demand_growth',val,'percent/year')
indicator('R19',15,'Paragraph 17','2017','recorded_peak_load',2972,'MW','Served peak, not unconstrained demand.')
indicator('R19',17,'Paragraph 22','2018','recorded_peak_load',3146,'MW','Excludes unmet demand during shedding.')
indicator('R19',17,'Paragraph 22','2019 report seasonal context','peak_summer_load_shed_upper_bound',40,'percent','As much as during June/July peak hours; not annual unserved-energy share.')
indicator('R19',22,'Paragraph 36 and footnote 4','2018','estimated_electricity_access',32,'percent','Connection-based estimate; source explicitly warns against comparing directly with household-survey access.')
indicator('R19',22,'Paragraph 35','preceding years; 2019 report','average_connection_fee',4500,'SDG/connection','Customer fee, not full network-extension cost; location and FX vary.')
indicator('R19',23,'Paragraph 37','mid-2018','solar_home_systems_distributed',15000,'systems','Compare R18 p44 claim of 1500; unresolved discrepancy.')
for sector,tonnes,share in [('HFO',198420,11.7),('HCGO',158663,9.3),('Diesel',25845,1.5),('LDO',448861,26.4),('SC',136181,8),('Crude oil',731962,43.1)]:
    add('thermal_fuel_use_2017','R19',19,'Table 1.4','2017','reported_utility_statistics',
        'Mass consumption; heat content and plant allocation needed for energy or emissions conversion.',fuel=sector,quantity_tonnes=tonnes,share_percent=share)
for appliance,ownership,number in [('TV',78.7,1.1),('Radio',27,1),('Computer',8.4,1.2),('Refrigerator',59.8,1.1),('Fan',73.9,2.7),('Air conditioning',22.6,1.5)]:
    add('appliance_ownership_2014','R19',18,'Table 1.3','2014','reported_survey_statistic',
        'Grid-connected households only. Average-unit denominator not further specified; power ratings and usage hours absent.',
        appliance=appliance,households_owning_percent=ownership,average_units_as_printed=number)
for fuel,v in [('fossil_fuels',6.46),('coal',0),('nuclear',0),('hydro',10),('other_renewables',.14),('total',16.6)]:
    indicator('R05',3,'Table 1','2021 table heading','generation_'+fuel,v,'TWh','Narrative PDF p8 calls 16.6 TWh 2020; retain table year and resolve against EIA series before calibration.')
indicator('R05',8,'Electricity section','2021','installed_capacity',4.5,'GW','Capacity basis differs from 2022 net series; narrative renewable percentages contain an error.')
for geo,v in [('Sudan',62),('Sudan urban',84),('Sudan rural',49)]:
    indicator('R05',8,'Electricity section','2021','population_electricity_access',v,'percent','Rounded estimates attributed to World Bank.',geography=geo)
for geo,v in [('Sudan',63.2),('Sudan urban',84),('Sudan rural',49.4)]:
    indicator('R18',43,'Energy and electricity; printed p44','2022','population_electricity_access',v,'percent',
              'Secondary/model report; reconcile with original access series. Does not assign service to individual settlements.',geography=geo)
for geo,v in [('Sudan',62.3),('Sudan urban',83.2),('Sudan rural',40.7)]:
    indicator('R18',44,'Current Path; printed p45','2043','population_electricity_access',v,'percent',
              'IFs Current Path projection, not an observed datum or electrification optimization result.',kind='model_projection',geography=geo)

# Published model assumptions: no automatic adoption as local wartime prices.
for name,v,u in [('capital_cost_system',2993,'USD/system'),('PV_rating',2,'kW'),('annual_O&M_system',60,'USD/system/year'),
 ('discount_rate',10,'percent'),('lifetime',20,'years'),('reported_annual_output',3523,'kWh/year'),
 ('performance_ratio',.9,'fraction'),('daily_yield_before_performance_ratio',5,'kWh/kWp/day'),('fuel_cost',0,'USD/year')]:
    param('R03',5,'Table 1 and Equation 2','2023 paper; quote date unspecified','2 kW Khartoum rooftop system',name,v,u,
          'Local contractor case with battery included per p9; not panel-only CAPEX. Published yield does not equal 365*2*0.9*5. Supplements not supplied.')
param('R03',5,'Methodology tariff assumption','2022-01','grid','customer_tariff',.015,'USD/kWh','Subsidized customer tariff, not economic grid supply cost.')
for name,v,u in [('project_life',25,'years'),('discount_rate',8,'percent'),('load_served',100,'percent'),
 ('PV_CAPEX',883,'USD/kW'),('wind_CAPEX',1355,'USD/kW'),('PV_annual_O&M',14,'USD/kW/year'),
 ('wind_annual_O&M',15,'USD/kW/year'),('battery_CAPEX',1250,'USD/battery'),('battery_annual_O&M',15,'USD/battery/year')]:
    param('R08',12,'Model assumptions','2022 paper','irrigation PV-wind-battery',name,v,u,
          'PV/wind CAPEX uses IRENA 2020 global averages, not Sudan quotations. Battery Surrette 4KS25P; do not convert cost per battery to cost per kWh without verified specification.',
          price_year='2020' if name in ['PV_CAPEX','wind_CAPEX'] else '')
for tech,cost,cf in [('PV',800,20),('wind',950,35)]:
    param('R19',42,'Table 3.5','2019 study',tech,'CAPEX',cost,'USD/kW','Historical planning assumption, not a Sudan wartime installed quote.')
    param('R19',42,'Table 3.5','2019 study',tech,'capacity_factor',cf,'percent','Assumption; replace with hourly resource and technology model.')
for tech,year,cost,real,nominal,loan,irr,ppa_esc,storage in [('GEMASOLAR',2011,12003.06,8.2,10.9,8,15,1,15),('ANDASOL-1',2008,8453.34,8,10.7,7,12,0,7.5)]:
    for name,v,u in [('CAPEX_net_capacity',cost,'USD/kW'),('real_discount_rate',real,'percent'),('nominal_discount_rate',nominal,'percent'),
      ('loan_rate',loan,'percent/year'),('target_IRR',irr,'percent'),('loan_term',20,'years'),('analysis_period',25,'years'),
      ('inflation',2.5,'percent/year'),('PPA',.15,'USD/kWh'),('PPA_escalation',ppa_esc,'percent/year'),('availability',96,'percent')]:
        param('R06',18,'Table 11 and section 4.3',str(year)+' cost basis; 2022 study',tech,name,v,u,
              'Spanish reference plant costs and SAM financing assumptions; no local Sudan quote.',price_year=str(year) if name.startswith('CAPEX') else '')
    param('R06',17,'Tables 9 and 10','2022 study',tech,'thermal_storage_duration',storage,'hours','Thermal storage; not battery duration.')

# Agricultural sites are weather-station coordinates, NOT surveyed project sites.
site_rows=[('North East of Karima','54-Karima',31.85,18.55,'arid','Poorly graded sand'),
 ('South East of Abuhamad','63-Abu-Hamed',33.31,19.53,'arid','Poorly graded silty sand'),
 ('Osaif','8-Dongonab',37.13,21.1,'arid','Silty sandy gravel'),('South west of Toker','59-Tokar',37.73,18.43,'arid','Silty gravelly sand'),
 ('West of Almatama','38-Khartoum',32.55,15.6,'arid','Gravelly silty sand'),('Kassala','41-Kassala',36.4,15.46,'semi-arid','Silty clay'),
 ('Elgurashi','27-Ed-Dueim',32.33,14,'semi-arid','Silty clay'),('Kadugli','9-Kadugli',29.71,11,'semi-arid','Sandy silty clay'),
 ('Almujlad','7-Babanusa',27.81,11.33,'semi-arid','Silty clay'),('Algadarif','34-Gadaref',35.4,14.03,'semi-arid','Silty clay'),
 ('Kutum North of Darfur','33-Kutum',24.66,14.2,'semi-arid','Silty clay'),('Wadi-Halfa','3-Wadi-Halfa',31.48,21.01,'arid','Poorly graded sand')]
for n,(name,station,lon,lat,climate,soil) in enumerate(site_rows,1):
    add('irrigation_weather_sites','R08',7,'Table 1','2022 paper','study_site',
        'Coordinates are nearest CLIMWAT weather station; no verified join to DRE clusters. Model assumes 1 hectare each of wheat cotton and sorghum; borehole depths 40-80 m.',
        site_number=n,sample_location=name,weather_station=station,longitude=lon,latitude=lat,climate=climate,soil=soil)
results='''1 i 31.4 0 21 16.4 70987 .417 75.1
1 ii 31.2 1 21 15.9 73010 .429 75.8
2 i 32.9 0 20 9.35 68183 .362 73.6
2 ii 32.1 1 19 9.43 68302 .362 73.9
3 i 14.3 0 10 4.88 31960 .496 73.6
3 ii 13.8 1 9 4.99 32450 .504 73.9
4 i 32.3 0 14 7.62 57485 .508 82.3
4 ii 28.5 1 15 7.71 57729 .510 80.6
5 i 24.7 0 17 10.1 55516 .377 71
5 ii 25.2 1 16 14.7 58803 .399 72.8
6 i 9.11 0 1 .130 10832 .609 91.8
6 ii 8.85 1 1 .260 11411 .641 92.3
7 i 14.8 0 1 .130 16595 .687 93
7 ii 15.1 1 1 .260 19396 .803 93
8 i 4.03 0 2 15 13234 .939 83
8 ii 2.79 1 2 18.3 15750 1.12 79.5
9 i 11.9 0 1 .680 13612 .814 93.8
9 ii 11.5 1 1 .521 15811 .945 93.9
10 i 6.48 1 6 4.46 20125 .658 81
10 ii 7.53 0 7 4.68 20386 .666 81.9
11 i 21.4 0 1 .13 23222 1.15 96.2
11 ii 21.4 1 1 .26 25723 1.28 96.3
12 i 22.8 2 17 9.71 58312 .379 72.5
12 ii 29.3 0 17 11.1 61656 .400 76.1'''
for line in results.splitlines():
    site,case,pv,wind,batt,conv,npc,coe,excess=line.split()
    add('irrigation_model_results','R08',13,'Table 2','2022 paper','model_result',
        'Published HOMER outputs, not independently replicated. COE header prints $; interpreted as USD/kWh from cost-of-electricity context. Very small converter values preserved.',
        site_number=int(site),case=case,PV_kW=float(pv),wind_kW=float(wind),battery_count=int(batt),converter_kW=float(conv),
        NPC_USD=float(npc),COE_USD_per_kWh=float(coe),excess_generation_percent=float(excess))

zones=[('Northern',21.95,30.9,304,7.89,3.51,24.86,12.024),('Northern',21.86,31.74,341,7.81,3.3,25.38,12.024),
 ('North Darfur',15.7,26.09,884,7.62,3.24,25.62,12.0175),('North Darfur',15.35,26.67,856,7.52,4.49,26.88,12.0175),
 ('North Darfur',15.25,25.44,952,7.64,4.23,24.05,12.014),('South Darfur',13.25,26.25,802.7,7.45,3.34,25.62,12.014)]
for n,(state,lat,lon,elev,dni,wind,temp,day) in enumerate(zones,1):
    add('csp_candidate_zones','R06',14,'Table 6; printed p13','2022 paper; resource period unspecified in table','study_site',
        'Candidate zone, not operating plant. NASA POWER daily-average resources; simulation TMY uses PVGIS 2007-2016. Grid proximity includes proposed lines.',
        zone=n,state=state,latitude=lat,longitude=lon,elevation_m=elev,DNI_kWh_per_m2_day=dni,wind_at_2m_m_per_s=wind,
        temperature_C=temp,daylight_hours=day,water_source='surface/groundwater' if n<3 else 'groundwater')
for technology,rows in [
 ('GEMASOLAR',[(140,91.948,.102957,461087),(140,91.8245,.10309,459042),(132,86.3926,.109318,427852),(125,81.7773,.115261,402257),(127,83.5173,.112943,417515),(119,78.3187,.120172,395700)]),
 ('ANDASOL-1',[(255,58.7892,.148796,926343),(257,59.2883,.147572,928716),(250,57.6696,.151623,888829),(237,54.7545,.159521,832964),(243,55.953,.156174,868540),(229,52.7389,.165494,826579)])]:
    for n,(energy,cf,lcoe,water) in enumerate(rows,1):
        page=19 if technology=='ANDASOL-1' and n>4 else 18
        add('csp_model_results','R06',page,'Table 12' if technology=='GEMASOLAR' else 'Table 13','2022 paper; 2021 LCOE cost case','model_result',
            'Solar-only published simulation; reference Spanish designs. Not observed capacity factor, local quote, or a settlement recommendation.',
            zone=n,reference_technology=technology,solar_only_generation_GWh=energy,solar_only_capacity_factor_percent=cf,
            solar_only_real_LCOE_2021_costs_USD_per_kWh=lcoe,solar_only_water_m3_per_year=water)

# Policy commitments are optional scenario targets, not existing capacity.
for number,measure,gwh,co2,cost in [(1,'Utility grid solar and wind',5056,3574580,1872),
 (2,'Standalone and mini-grid residential agricultural industrial',1529,1086360,846),
 (3,'Hydro rehabilitation',37,26221,6),(4,'Transmission and distribution loss reduction',1213,857506,210),
 (5,'Residential appliance efficiency',2295,463759,5)]:
    add('ndc_electricity_targets','R10',9,'Table 3-2; printed p5','2030 target in 2021 NDC','policy_target',
        'Conditional on international support per PDF p8. Displaced electricity is not installed MW; costs are programme estimates, not component CAPEX.',
        measure_number=number,measure=measure,electricity_displaced_GWh=gwh,emission_reduction_tCO2e=co2,programme_cost_million_USD=cost)

for title,count,budget,beneficiaries in [('Health PV systems',150,7.5,1.3),('Solar water pumps',20000,140,1.12),
 ('Solar water yards',1000,50,3),('Solar home systems',100000,50,.6),('Productive-use mini-grids',50,2.5,.03)]:
    add('programmes_and_projects','R15',39,'Box 6-1; printed p36','2020 concept; five-year programme','proposed_programme',
        'Concept, not delivery evidence. Budget includes unspecified scope; do not divide by count to estimate hardware price. Line budgets sum to 250 million; stated beneficiaries sum to 6.05 million but may overlap.',
        project=title,location='Sudan',quantity=count,quantity_unit='systems',budget_million_USD=budget,beneficiaries_million=beneficiaries)
for title,loc,number,unit,page,kind in [('Solar irrigation systems','River Nile',350,'systems',5,'reported_project_output'),
 ('Solar powered health facilities','Sudan',110,'clinics and hospitals',7,'reported_project_output'),
 ('Clean energy beneficiaries','Sudan',600000,'people; more than',7,'reported_project_output'),
 ('Solar water pumps finance pilot','River Nile',60,'pumps expected in 2025',7,'planned_project')]:
    add('programmes_and_projects','R16',page,'Annual report 2024; printed spreads 8-9 or 12-13',
        '2025 planned' if kind=='planned_project' else '2024 reporting',''+kind,
        'No site coordinates or system kW/kWh given. Beneficiaries may overlap; do not sum with other programmes.',
        project=title,location=loc,quantity=number,quantity_unit=unit,budget_million_USD=None,beneficiaries_million=None)
for title,loc,n,budget,period in [('UNDP GEF solar pumping','Northern',1469,5,'2016 programme'),
 ('UNDP KOICA solar pumping','River Nile',450,7,'2020 programme'),('AfDB solar pumping','North and West Kordofan',1200,21.7,'2020 report; proposed')]:
    add('programmes_and_projects','R15',22,'Box 2-2; printed p19',period,'reported_programme',
        'Secondary project summary; count is programme scope, not verified installation count. AfDB quantity nearly 1200. Budget scope and equipment sizes unknown.',
        project=title,location=loc,quantity=n,quantity_unit='solar pumps',budget_million_USD=budget,beneficiaries_million=None)
for title,n,budget,period,loc,note in [('GEF irrigation programme',None,5.3,'2016 funding','Sudan','Table 1 budget differs from R15 Box 2-2; programme scopes need reconciliation.'),
 ('Kassala water-pump solar systems',2,None,'2024','Kassala','Table 2 cites two pumps; water supply rises from 200000 to 450000 litres/day; no electrical capacity.'),
 ('ASCENT solar systems',500,76.3,'2025 approval','Gadaref Kassala Northern River Nile','Target, despite table caption calling projects completed. Budget also includes digital access; not solar-only cost.'),
 ('IICO solar systems',8,None,'2025','River Nile and Al Qadarif','Six water stations, one hospital, one health centre; secondary report, sizes absent.')]:
    add('programmes_and_projects','R01',3 if period=='2016 funding' else 4,'Table 1' if period=='2016 funding' else 'Table 2',period,
        'planned_project' if title.startswith('ASCENT') else 'secondary_project_report',note,
        project=title,location=loc,quantity=n,quantity_unit='systems' if n else '',budget_million_USD=budget,beneficiaries_million=None)

darfur_projects=[('Nyala thermal 5 MW',8.2,0,8.2,5),('Nyala thermal 20 MW',35.1,0,35.1,20),
 ('El Fasher overhaul six generators',6,0,6,None),('Central Darfur generation and connections',22.9,22.9,45.8,None),
 ('Nyala solar',13.4,0,13.4,5),('El Fasher solar',8.5,0,8.5,3),('El Geneina solar',6,0,6,2),('Zalingei solar',5.3,0,5.3,1.75),
 ('Nyala wind',0,46.2,46.2,20),('Rural solar home systems',37.2,37.3,74.5,None),
 ('Tegabo and Medop geothermal study',1,0,1,None),('Babanousa Adila Ed Daein Nyala El Fasher grid extension',140,100,240,None),
 ('Nyala Kass Zalingei ElGeneina grid extension',100,105,205,None),('Distribution network expansion',120,180,300,None),
 ('Electrification master plan',2,0,2,None),('Energy capacity building',1.5,1.5,3,None)]
for title,early,late,total,cap in darfur_projects:
    add('darfur_investment_plan','R02',75,'Annex 8; printed p62','2013-2019 planned phases','planned_project',
        'Consultant and Ministry estimates; no commissioning evidence. Unit length and detailed scope absent. Dash normalized to zero only for phase-budget addition.',
        project=title,budget_2013_2016_million_USD=early,budget_2017_2019_million_USD=late,total_budget_million_USD=total,proposed_capacity_MW=cap)

# Qualitative evidence gives mechanisms for scenarios, without invented probabilities.
qualitative=[
 ('R12',7,'Paragraph 8','2024-08 context','National grid','Two operational islands after damage; dispatch coordinated manually after loss of the dispatch centre.','Test north/south separation with explicit corridor outages; verify topology first.'),
 ('R12',6,'Paragraphs 5-6','2024-08','Kosti and demand-hosting states','Fuel interruption limits thermal operation; displacement shifts demand to northern and eastern states.','Separate fuel constraint from destroyed capacity; vary spatial demand independently.'),
 ('R12',3,'Summary and PDF p6','2024-08','Khartoum and Gazira','Summary attributes 75% of former demand to these areas; body says two thirds.','Retain discrepancy; no automatic regional demand scaling.'),
 ('R17',30,'Sections 6.2.3-6.2.5; printed p28','2025 interviews','Solar supply chain','Direct purchases may require full containers and full prepayment; delays and inland permissions raise delivery costs.','Separate procurement lead time, working capital and route costs from equipment price.'),
 ('R17',30,'Section 6.2.4; printed p28','2025 interviews','Solar quality','Reports of damaged equipment and misleading capacity labels; no representative failure-rate estimate.','Quality/derating sensitivity; obtain warranty and test certificates, do not invent failure probabilities.'),
 ('R17',30,'Section 6.2.5; printed p28','2025 interviews','Port Sudan','Clearance delays reported up to 2.5 months; fines in some cases up to USD 200/day.','Anecdotal upper examples; project-specific construction delay scenario, not mean values.'),
 ('R17',20,'Table 4.1; printed p18','2023-10 to 2023-11','Eight states','MSME analysis draws on 16 focus groups of 8-10 participants; purposive mix of solar users and non-users.','Use as qualitative evidence; not nationally representative outage probabilities. Appendix gives October-December instead.'),
 ('R09',8,'Table 4','2024 paper','Oil infrastructure','Two-to-five-year overhaul estimates refer to petroleum facilities; no electrical asset repair schedule.','Fuel recovery scenario motivation only; do not apply these durations to every power plant or line.'),
 ('R09',9,'Section 5.6','2024 paper','Kosti and Garri','Shutdowns attributed to fuel feedstock shortages; reported generation figures differ from nameplate capacities.','Cross-check against dated World Bank inventory; operational output is not installed capacity.'),
 ('R01',3,'Section 2.2','2026 paper','Governance','Proposed sustainability unit would support maintenance funding, oversight, training and monitoring.','Include O&M staffing and replacement budgets; proposal is not an existing institution or measured cost.'),
 ('R04',2,'Governing law','2023 guide','Sudan','Lists electricity legislation, 2019 amendments and 2021 PPP framework.','Historical legal source lead; verify current approvals separately before implementation.'),
 ('R04',3,'PPAs and approvals','2023 guide','Sudan','Guide says no private producers or PPAs to its knowledge; WB2019 describes rental semi-IPP PPAs.','Scope conflict; do not assume net metering or bankable purchase agreement exists.'),
 ('R15',39,'Theme 1','2020 roadmap','Rural Sudan','Energy access designed around health, irrigation, household and productive uses, with gender and affordability priorities.','Compare service levels and productive loads, not only minimum household lighting.'),
 ('R18',43,'Energy and electricity; printed p44','2026 report','Sudan','Text says natural-gas development stalled, whereas p26 IFs energy series assigns substantial gas production.','Avoid using IFs primary-energy series as an electricity fuel balance.'),
 ('R14',1,'Map and legend','2023 labels; author publication date unknown','Sudan','Map lists Roseires 1800 MW and Al Fula 540 MW; conflicts with WB inventories and project-status evidence.','Quarantine map asset quantities and line status; illustration is not an engineering network database.')]
for src,p,ref,period,loc,finding,use in qualitative:
    add('scenario_evidence',src,p,ref,period,'qualitative_report',finding,location=loc,model_application=use)

issues=[
 ('R17',29,'panel_power_unit','590 kW printed for a solar panel.','No correction inferred; power-normalized price blocked.'),
 ('R17',29,'shipment_denominator','22 percentages total approximately 100 but equipment cost and quantities withheld.','Not a national CAPEX uplift; no hardware/logistics ratio.'),
 ('R17',31,'battery_energy_missing','200 Ah prices lack voltage, chemistry and usable depth of discharge.','Do not convert to kWh.'),
 ('R17',20,'focus_group_dates','Main section October-November 2023; appendix p49 October-December 2023.','Use 2023 evidence, preserve date discrepancy.'),
 ('R12',12,'upper_atbara_grid','Annex places Seitat/Upper Atbara North; p7 narrative places it South.','Grid assignment unresolved.'),
 ('R12',11,'asset_years','Kosti year 2008 conflicts with 2015 commissioning stated in WB2019 p15-16; Garri1/2 2008 differs from WB2019 2002.','Year as printed; not used as build_year.'),
 ('R12',13,'nyala_capacity','Nyala 10 MW in 2024 annex versus 32 MW in 2019 annex and 29.19 MW in 2012 table.','Do not interpret differences as destroyed MW without asset scope reconciliation.'),
 ('R12',5,'fleet_total','Prewar headline 3700 MW is not the sum of Annexes 1-2 and differs from baseline 4209 MW net capacity.','Keep scope/vintage differences; no rescaling.'),
 ('R12',3,'khartoum_gazira_share','75% in summary versus two thirds on p6.','Not a validated regional load split.'),
 ('R02',31,'zalingei_availability','Table 1.0 MW versus same-page narrative 0.8 MW.','Table retained; narrative discrepancy documented.'),
 ('R03',5,'PV_yield_arithmetic','365*2*0.9*5 = 3285 kWh/year, while Table 1 gives 3523.','Preserve reported inputs; replication requires supplement or author clarification.'),
 ('R06',12,'line_length_total','Existing lengths965.5+7692.9+1128.7+233 sum to10020.1km; printed total10010.1km.','Keep detailed rows;10km discrepancy reported by validator.'),
 ('R19',51,'revenue_scale','Revenue headed SDG millions but 2017 total 4445397 conflicts with about SDG4.3bn in p30.','Revenue section excluded from numeric collection pending unit resolution.'),
 ('R19',18,'capacity_inconsistency','Text about 3500 MW; figure note 3676 MW; figure Upper Atbara 350 versus Annex 320 MW.','Annex retained as historical inventory; no asserted national total.'),
 ('R19',49,'pipeline_scope','Pipeline includes 1175 MW Port Sudan upgrade and other proposed projects.','Preserve printed values; never count pipeline as commissioned fleet.'),
 ('R19',50,'tariff_USD_rounding','0.70/47.6 does not round to printed government tariff 0.016 USD/kWh.','Preserve both source columns; use SDG for historical tariff and document chosen FX.'),
 ('R19',42,'savings_units','Table3.4 columns labelled million USD contain values consistent with thousands; wind capacity text120 vs table150.','Savings table not treated as directly usable financial data.'),
 ('R19',56,'least_cost_forecast','Table A0.2 differs slightly from Table3.2; 2023 entries are forecasts.','No forecast capacity used as observation.'),
 ('R05',8,'energy_year_and_share','2021 Table1 generation is called 2020 in text; fossil about50% + hydro43% + other57% exceeds100%.','Keep table year; exclude erroneous shares; trace original EIA series.'),
 ('R14',1,'map_capacity','Roseires 1800 MW and several proposed/unverified thermal plants conflict with stronger records.','Quarantine numerical map inventory; do not digitize as operational network.'),
 ('R18',26,'primary_energy_gas','IFs text reports gas output while p43 says development stalled; primary energy differs from electricity.','Do not calibrate electricity from these BOE figures.'),
 ('R18',44,'SHS_count_and_target','1500 homes by2018 vs WB2019 15000 SHS; 80% access target vs WB universal access with80%grid.','Keep distinct scope claims; use original programme records.'),
 ('R18',46,'rural_projection_conflict','Current Path rural2043 access40.7% on p44 versus47% on p46.','Retain p44 value with conflict flag; do not treat as observed demand.'),
 ('R01',4,'project_status_caption','Caption says completed projects but ASCENT description is future targets.','ASCENT coded planned; digital budget not solar CAPEX.'),
 ('R08',13,'simulation_not_observation','High excess generation and small converter ratings may require original HOMER files to explain.','Preserve outputs; not independently validated or applicable to settlement household demand.')]
for src,p,issue,detail,action in issues:
    add('source_issues',src,p,'Review finding','review 2026-10-17','source_issue',detail,issue_code=issue,handling=action)

# Reusable national planning comparison: forecast results, explicitly not actual 2023 fleet.
for carrier,lcap,gcap,lgen,ggen in [('Coal',600,600,4468,4730),('Coke',110,110,819,819),('Diesel',99,99,0,0),
 ('HFO',2438,3668,4725,6023),('LFO',580,1030,938,401),('Hydro',1974,1974,11412,11412),
 ('Solar',810,660,1539,1254),('Wind',800,240,1265,380),('Imports',500,390,2799,2946),('Total',7911,8771,27965,27965)]:
    add('generation_plan_comparison','R19',40,'Table 3.2','2023 forecast made in 2019','model_result',
        'Historical least-cost versus government plan. Imports included in capacity total; annual sums subject to source rounding. Not observed capacity.',
        carrier=carrier,least_cost_capacity_MW=lcap,government_capacity_MW=gcap,
        least_cost_generation_GWh=lgen,government_generation_GWh=ggen,is_total=carrier=='Total')
for metric,value in [('grid_households_approx',2000),('no_lighting_households_approx',1300),('other_lighting_households',770),
 ('firewood_lighting_households',290),('solar_lighting_households',208)]:
    indicator('R17',16,'Section 2.5; Figure 2.7 narrative','2022-06 survey',metric,value,'sampled households',
        'Reported sample counts, not population-weighted access rates. Survey total4878 households; full categories and weights require microdata.',
        kind='reported_sample_count')
for period,metric,value in [('early 2017','PV_import_unit_price',.38),('mid-2025','PV_import_unit_price_lower',.05),('mid-2025','PV_import_unit_price_upper',.10)]:
    indicator('R17',13,'Section 2.4; printed p11',period,metric,value,'USD/W',
        'Ember/GACC import-value ratio; not installed or retail system cost. Raw monthly trade dataset needed; imports do not prove commissioning.',kind='reported_trade_statistic')

leads=[
 ('R17',12,'Ember China solar exports / GACC','https://ember-energy.org/data/china-solar-exports-data/','Monthly panel/cell trade value and capacity','Recover numeric time series behind Figures2.1-2.6; check trade routes and price denominator.','named_in_report_not_downloaded'),
 ('R17',12,'Ember export explorer','https://ember-energy.org/data/chinas-solar-pv-export-explorer/','Country monthly solar imports','Use original data rather than digitizing charts; never equate imports with operating capacity.','named_in_report_not_downloaded'),
 ('R17',15,'Sudan Labor Market Panel Survey 2022; Krafft Assaad Cheung 2024','', 'Household lighting access and business characteristics','Request ERF microdata and sample weights; validate household-based demand segmentation.','named_in_report_not_downloaded'),
 ('R17',20,'Ali et al. 2024 MSME energy transition focus groups','', '16 focus groups across8 states in2023','Request questionnaires and transcripts with permissions; evidence of mechanisms not probability estimates.','named_in_report_not_downloaded'),
 ('R08',7,'FAO CLIMWAT / CROPWAT','', 'Climate soil crop water requirement','Build seasonal irrigation loads using crop calendars head pump efficiency and cultivated area.','named_in_report_not_downloaded'),
 ('R08',7,'British Geological Survey hydrogeology','', 'Borehole depth and aquifers','Validate pumping head locally; depth is not total dynamic head.','named_in_report_not_downloaded'),
 ('R06',12,'NASA POWER','', 'Hourly/daily solar and meteorology','Retrieve common weather years; verify locations and irradiance units.','named_in_report_not_downloaded'),
 ('R06',14,'PVGIS TMY','', 'TMY EPW weather2007-2016 used by CSP study','Replication weather source; a TMY is not measured2022 chronology.','named_in_report_not_downloaded'),
 ('R06',18,'NREL SAM and CSP cost database','', 'CSP technical and financial assumptions','Obtain original SAM projects before claiming replication; foreign costs need localization.','named_in_report_not_downloaded'),
 ('R03',5,'Ahmed et al. online supplementary Appendices1-3','https://doi.org/10.1093/ce/zkad044','Contractor quote and COE worksheet','Resolve annual-yield discrepancy and battery/export assumptions.','not_in_supplied_folder'),
 ('R19',39,'Sudanese Electricity Distribution Company GIS','', 'HV/MV lines and settlement map','Request original geospatial layers voltage ratings build date and operating status; PDF map insufficient.','request_from_data_owner'),
 ('R19',51,'Sudanese Electricity Distribution Company accounts','', 'Sales customer counts and revenue','Request2022 state/sector monthly sales and clarify revenue units.','request_from_data_owner'),
 ('R12',11,'Sudan Electricity Company plant status inventory','', 'August2024 operational status','Request dated unit-level operating MW maintenance fuel restrictions and georeferenced substations.','request_from_data_owner'),
 ('R05',3,'EIA International Energy Statistics','', 'Generation and capacity historical series','Resolve2020/2021 narrative-table conflict and gross/net definitions.','named_in_report_not_downloaded'),
 ('R18',10,'International Futures project data and scenario files','', 'Macro demand and development projections','Use as scenario drivers only after resolving gas/access discrepancies; not electricity dispatch data.','named_in_report_not_downloaded'),
 ('R11',1,'World Bank VIDA Sudan DRE Atlas','https://energydata.info/dataset/sudan-distributed-renewable-energy-dre','33891 settlement clusters and demand proxy','Reuse repository spatial collection; historic risk is2020-2022.','already_in_repository'),
 ('R13',1,'Lahmeyer2012 forecasting report','', 'Plant heat rates hydro monthly series locality forecasts','Reuse repository historical collection; distinguish forecasts from observations.','already_in_repository')]
for src,p,owner,url,content,use,status in leads:
    add('data_source_leads',src,p,'Named source or underlying data owner','mixed source vintages','data_source_lead',
        'URLs recorded from supplied PDFs; availability not rechecked during this local review.',
        data_owner_or_resource=owner,url=url,content=content,next_action=use,acquisition_status=status)

def write_tables():
    for name,rows in TABLES.items():
        fields=list(dict.fromkeys(k for row in rows for k in row))
        with (ROOT/(name+'.csv')).open('w',encoding='utf-8',newline='') as f:
            w=csv.DictWriter(f,fieldnames=fields,lineterminator='\n'); w.writeheader(); w.writerows(rows)
    print(json.dumps({k:len(v) for k,v in TABLES.items()},indent=2))

if __name__=='__main__':
    write_tables()
