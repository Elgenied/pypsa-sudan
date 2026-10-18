"""Inventory the proposed northern-central study; does not optimize a regional plan."""
from pathlib import Path
import hashlib
import json
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
CORE = ['Northern', 'River Nile', 'Khartoum', 'Gezira', 'White Nile', 'Sennar']


def prepare():
    source = ROOT / 'research/dre_atlas_2025/data/settlement_attributes.csv.gz'
    out = ROOT / 'data/north_central_study'
    out.mkdir(parents=True, exist_ok=True)
    atlas = pd.read_csv(source)
    assert atlas.geohash.is_unique
    selected = atlas.loc[atlas.admin_cgaz_1.isin(CORE)].copy()
    selected['proposed_scope'] = 'core'
    # Preserve every source cluster, including large urban clusters and nightlight sites.
    columns = ['geohash', 'admin_cgaz_1', 'proposed_scope']
    selected[columns].sort_values(['admin_cgaz_1', 'geohash']).to_csv(
        out / 'scope_membership.csv', index=False, lineterminator='\n')
    rows = []
    for state in CORE:
        group = selected.loc[selected.admin_cgaz_1.eq(state)]
        rows.append(dict(state=state, proposed_scope=group.proposed_scope.iloc[0],
                         source_clusters=len(group),
                         potential_building_connections=int(group.num_connections.sum()),
                         atlas_formula_kWh_per_day=float(group.demand.sum()),
                         source_nightlight_true_clusters=int(group.has_nightlight.sum()),
                         source_grid_distance_missing=int(group.distance_to_existing_transmission_lines.isna().sum())))
    summary = pd.DataFrame(rows)
    summary.to_csv(out / 'coverage.csv', index=False, lineterminator='\n')
    manifest = dict(status='scope_inventory_only_not_optimized',
                    source=source.relative_to(ROOT).as_posix(),
                    source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                    core_states=CORE,
                    core_clusters=int(summary.loc[summary.proposed_scope.eq('core'), 'source_clusters'].sum()),
                    selection='All source clusters in the declared states; no size, distance, nightlight or risk exclusion.',
                    interpretation='Counts describe atlas coverage, not verified households, access deficits or new connections. Atlas formula demand is not added to national demand.',
                    regional_optimization_completed=False)
    assert len(selected) == summary.source_clusters.sum()
    (out / 'scope_manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    print(summary.to_string(index=False))


if __name__ == '__main__':
    prepare()
