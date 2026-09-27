"""Execute the spatial notebook in the pypsa environment and export readable HTML."""

from pathlib import Path
import argparse

import nbformat
from nbclient import NotebookClient
from nbconvert import HTMLExporter


ROOT = Path(__file__).resolve().parent
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--kernel", default="python3")
parser.add_argument("--export-only", action="store_true")
args = parser.parse_args()
path = ROOT / "Sudan_DRE_Settlements.ipynb"
nb = nbformat.read(path, as_version=4)
if not args.export_only:
    NotebookClient(nb, timeout=600, kernel_name=args.kernel, resources={"metadata": {"path": str(ROOT)}}).execute()
    nbformat.write(nb, path)
exporter = HTMLExporter(template_name="lab")
exporter.exclude_input = True
body, _ = exporter.from_notebook_node(nb)
(ROOT / "Sudan_DRE_Settlements.html").write_text(body, encoding="utf-8")
print("Exported" if args.export_only else "Executed and exported", path)
