"""Freeze an eight-cluster extension and the existing national reference inputs."""
from pathlib import Path
import json, shutil, hashlib
import pandas as pd
import networkx as nx
from prepare_recovery import distance, ANCHOR

ROOT=Path(__file__).resolve().parents[2]
DATA=ROOT/'data/national_coupling'

def prepare():
    DATA.mkdir(parents=True,exist_ok=True)
    source=ROOT/'research/dre_atlas_2025/data/settlement_attributes.csv.gz'
    atlas=pd.read_csv(source); anchor=atlas.set_index('geohash').loc[ANCHOR]
    eligible=atlas.loc[(atlas.admin_cgaz_1=='Blue Nile') & atlas.num_connections.between(20,500) & (atlas.hull_area>0) & ~atlas.has_nightlight].copy()
    eligible['distance_to_anchor_km']=[distance(anchor,s) for s in eligible.itertuples()]
    sites=eligible.sort_values(['distance_to_anchor_km','geohash']).head(8).copy()
    sites['site_id']=[f'S{i+1}' for i in range(len(sites))];sites['pilot_type']='nationally_coupled_neighbourhood'
    columns=list(pd.read_csv(ROOT/'data/recovery_planning/sites.csv').columns)
    sites[columns].to_csv(DATA/'sites.csv',index=False,lineterminator='\n')
    graph=nx.Graph();rows=list(sites.itertuples())
    for i,a in enumerate(rows):
        for b in rows[i+1:]:graph.add_edge(a.site_id,b.site_id,weight=distance(a,b)*1.3)
    selected={tuple(sorted(e)) for e in nx.minimum_spanning_tree(graph).edges}
    for a in graph:
        for b in sorted(graph[a],key=lambda b:(graph[a][b]['weight'],b))[:2]:selected.add(tuple(sorted((a,b))))
    routes=[dict(edge_id=a+'_'+b,from_site=a,to_site=b,route_km=graph[a][b]['weight'],capacity_MW=.4,efficiency=.98) for a,b in sorted(selected)]
    pd.DataFrame(routes).to_csv(DATA/'candidate_routes.csv',index=False,lineterminator='\n')
    config=dict(study='Eight-cluster planning coupled to the 19-node Sudan reference',daily_kWh_per_connection=1,
        national_bus='Roseires',national_reference_year=2022,national_time_conversion='Periodic annual series shifted from local UTC+2 to UTC; last two UTC hours use first two local-year hours.',
        national_cost_basis='Existing illustrative national variable costs assigned constant-2025 USD for this scenario, not converted observed prices.',
        national_scope='Fixed 2022 reference fleet, fixed imports/other generation, annual hydro budgets and schematic corridors; no national investment or war-damage inference.',
        incremental_demand_note='Selected clusters are assumed additional access demand, excluded from the existing aggregate consumer total by construction; actual overlap is unverified.',
        common_feeder_repair_km=float(anchor.distance_to_existing_transmission_lines)*1.3,repair_fraction_of_new_line=.35,
        common_feeder_capacity_MW=.4,common_feeder_efficiency=.98,
        feeder_mapping='Assumed access to the Roseires regional bus through the atlas-proximity feeder; no surveyed long-distance route or new line from Roseires city is claimed.',
        candidate_graph='Union of two-nearest-neighbour edges and geometric minimum spanning tree; all lengths great-circle x1.3, not surveyed.',
        weather_note='Shared existing Al Kurumuk NASA POWER 2022 series; maximum anchor separation %.3f km.'%sites.distance_to_anchor_km.max(),
        grid_hub='All grid-side PV/storage/diesel offered only at S1; non-root nodes may transit power while locally off-grid.',
        scenario_order=['constrained','partial','broad'],scenarios={
            'constrained':dict(label='Constrained local recovery',repair_budget_USD=0,outage_local_hours=[18,19,20,21,22,23]),
            'partial':dict(label='Partial local recovery',repair_budget_USD=30000,outage_local_hours=[19,20,21]),
            'broad':dict(label='Broad local recovery',repair_budget_USD=100000,outage_local_hours=[])},
        master_mip_gap=.00005,coupling_relative_tolerance=.0001,coupling_absolute_tolerance_USD=1.,maximum_iterations=8,
        money_basis='Constant 2025 USD; 20 years; 10% real discount; zero tax transfer; existing national assets sunk.')
    (DATA/'config.json').write_text(json.dumps(config,indent=2)+'\n')
    weather=ROOT/f'data/electrification_pilot/weather_{ANCHOR}_2022.csv.gz'
    for s in rows:shutil.copy2(weather,DATA/f'weather_{s.geohash}_2022.csv.gz')
    shutil.copy2(ROOT/'results/sudan_2022.nc',DATA/'national_reference.nc')
    shutil.copy2(ROOT/'results/national_2022.csv',DATA/'national_2022.csv')
    sources=dict(atlas_url='https://energydata.info/dataset/sudan-distributed-renewable-energy-dre',atlas_license='World Bank Group / VIDA CC BY 4.0',
        atlas_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),weather_source=f'data/electrification_pilot/weather_{ANCHOR}_2022.csv.gz',
        weather_provenance='data/electrification_pilot/source_manifest.json',national_reference_source='results/sudan_2022.nc',
        national_reference_sha256=hashlib.sha256((DATA/'national_reference.nc').read_bytes()).hexdigest(),
        national_method='Sudan_2022.ipynb; annual hydro budgets recreated from national_2022.csv because NetCDF does not retain custom constraints.',
        selection='Eight nearest eligible Blue Nile clusters to the existing Al Kurumuk anchor, 20–500 connections, positive area, no detected nightlight; ties by geohash. Selected before solving.')
    (DATA/'sources.json').write_text(json.dumps(sources,indent=2)+'\n')
    print(sites[columns].to_string(index=False));print('Candidate edges:',len(routes),'Connections:',sites.num_connections.sum())

if __name__=='__main__':prepare()
