"""Execute the notebook and export the readable HTML. Run in conda env pypsa."""
from pathlib import Path
import nbformat
from nbclient import NotebookClient
from nbconvert import HTMLExporter

root=Path(__file__).resolve().parent
path=root/'Sudan_Forecasting_Replication.ipynb'
nb=nbformat.read(path,as_version=4)
NotebookClient(nb,timeout=600,kernel_name='python3',resources={'metadata':{'path':str(root)}}).execute()
nbformat.write(nb,path)
exporter=HTMLExporter(template_name='lab')
exporter.exclude_input=True
body,_=exporter.from_notebook_node(nb)
(root/'Sudan_Forecasting_Replication.html').write_text(body,encoding='utf-8')
print('Executed notebook and exported HTML:',root)
