"""Execute the notebook and export the readable HTML. Run in conda env pypsa."""
from pathlib import Path
import argparse
import nbformat
from nbclient import NotebookClient
from nbconvert import HTMLExporter

root=Path(__file__).resolve().parent
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--kernel', default='python3')
parser.add_argument('--export-only', action='store_true')
args=parser.parse_args()
path=root/'Sudan_Forecasting_Replication.ipynb'
nb=nbformat.read(path,as_version=4)
if not args.export_only:
    NotebookClient(nb,timeout=600,kernel_name=args.kernel,resources={'metadata':{'path':str(root)}}).execute()
    nbformat.write(nb,path)
exporter=HTMLExporter(template_name='lab')
exporter.exclude_input=True
body,_=exporter.from_notebook_node(nb)
(root/'Sudan_Forecasting_Replication.html').write_text(body,encoding='utf-8')
print('Exported HTML' if args.export_only else 'Executed notebook and exported HTML',root)
