"""Build or verify the versioned factual data catalog (standard library only)."""
from pathlib import Path
import argparse, csv, hashlib, json

ROOT = Path(__file__).resolve().parents[1]
COLLECTION = ROOT / 'research/forecasting_2012'
CATALOG = ROOT / 'data/catalog.json'
EXCLUDE = {'raw_table_inventory.csv', 'plant_geometric_rows_unverified.csv'}

def build():
    entries = []
    for path in sorted((COLLECTION/'data').glob('*.csv')):
        if path.name in EXCLUDE:
            continue
        with path.open(encoding='utf-8-sig', newline='') as stream:
            reader = csv.DictReader(stream)
            rows = list(reader)
            columns = reader.fieldnames
        if not columns or not rows:
            raise ValueError(f'Empty dataset: {path.name}')
        if any(None in row for row in rows):
            raise ValueError(f'Unexpected extra CSV fields: {path.name}')
        external = path.name == 'implementation_crosscheck_2019.csv'
        entries.append({
            'id': path.stem,
            'path': path.relative_to(ROOT).as_posix(),
            'rows': len(rows), 'columns': columns,
            'sha256': hashlib.sha256(path.read_bytes().replace(b'\r\n', b'\n')).hexdigest(),
            'source': 'World Bank Sudan electricity diagnostic, 2019, Table 1.1' if external else
                      ('Source register: multiple original owners' if path.stem=='source_register' else
                       'MWRE / Lahmeyer, report 260690, final revision 2012-10-18'),
            'vintage_note': 'Project status as of 2019' if external else
                            'Mixed 2008 census, 2006–2011 observations, 2012 assumptions and 2012–2031 forecasts; see dictionary',
            'dictionary': 'research/forecasting_2012/DATA_DICTIONARY.md',
        })
    if len(entries) != 20:
        raise ValueError(f'Expected 20 public datasets; found {len(entries)}. Review the catalog schema when adding a dataset.')
    return {'schema_version': 1, 'collection_id': 'sudan_forecasting_2012',
            'checksum_basis': 'UTF-8 file bytes with CRLF normalized to LF, matching Git text normalization',
            'source_metadata': 'research/forecasting_2012/source_metadata.json',
            'rights_and_attribution': 'research/forecasting_2012/DATA_SOURCES_AND_RIGHTS.md',
            'datasets': entries}

if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    args=parser.parse_args()
    expected=build()
    if args.check:
        actual=json.loads(CATALOG.read_text(encoding='utf-8'))
        if actual != expected:
            raise SystemExit('Catalog differs from current data. Review changes and rerun python scripts/data_catalog.py.')
        print(f"Catalog verified: {len(expected['datasets'])} datasets.")
    else:
        CATALOG.parent.mkdir(exist_ok=True)
        CATALOG.write_text(json.dumps(expected, indent=2, ensure_ascii=False)+'\n',encoding='utf-8')
        print(f"Catalog updated: {len(expected['datasets'])} datasets.")
