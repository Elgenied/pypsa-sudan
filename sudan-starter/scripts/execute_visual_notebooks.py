"""Execute both visual notebooks and save embedded outputs plus HTML previews.

Requires nbformat, nbclient, nbconvert, ipykernel and a kernel named pypsa.
No model inputs or solved network files are modified.
"""
from pathlib import Path
import argparse
import nbformat
from nbclient import NotebookClient
from nbconvert import HTMLExporter

ROOT = Path(__file__).resolve().parents[1]

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kernel",default="pypsa")
    parser.add_argument("--export-only",action="store_true",help="Export already executed notebooks without rerunning cells")
    args = parser.parse_args()
    for name in ["01_explore_sudan", "02_reference_2022"]:
        path = ROOT / "notebooks" / f"{name}.ipynb"
        book = nbformat.read(path,as_version=4)
        if not args.export_only:
            NotebookClient(book,timeout=180,kernel_name=args.kernel,resources={"metadata":{"path":str(ROOT / "notebooks")}}).execute()
        # Successful execution can contain environment paths in diagnostic streams.
        # Keep visual/table outputs; remove diagnostic streams from the public copy.
        for cell in book.cells:
            if cell.cell_type == "code":
                cell.outputs = [o for o in cell.outputs if o.output_type != "stream"]
                assert all(o.output_type != "error" for o in cell.outputs)
        nbformat.validate(book)
        nbformat.write(book,path)
        exporter = HTMLExporter(template_name="lab",exclude_input=True)
        body,_ = exporter.from_notebook_node(book)
        (path.with_suffix(".html")).write_text(body,encoding="utf-8")
        print("Executed and exported",name,flush=True)

if __name__ == "__main__":
    main()
