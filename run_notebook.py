"""Execute the single model notebook and write a readable HTML preview."""
from pathlib import Path
import argparse
import nbformat
from nbclient import NotebookClient
from nbconvert import HTMLExporter

root = Path(__file__).resolve().parent
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--kernel', default='pypsa')
parser.add_argument('--export-only', action='store_true')
args = parser.parse_args()
path = root / 'Sudan_2022.ipynb'
book = nbformat.read(path, as_version=4)
if not args.export_only:
    NotebookClient(book, timeout=1800, kernel_name=args.kernel,
                   resources={'metadata': {'path': str(root)}}).execute()
    for cell in book.cells:
        if cell.cell_type == 'code':
            assert not any(output.output_type == 'error' for output in cell.outputs)
            # Keep results and figures; omit verbose solver streams and local runtime paths.
            cell.outputs = [output for output in cell.outputs if output.output_type != 'stream']
    nbformat.write(book, path)
html, _ = HTMLExporter(template_name='lab', exclude_input=True).from_notebook_node(book)
(root / 'Sudan_2022.html').write_text(html, encoding='utf-8')
print('Ready: Sudan_2022.ipynb and Sudan_2022.html')
