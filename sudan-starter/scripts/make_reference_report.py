"""Create the default historical-reference viewer from solved annual outputs."""
from pathlib import Path
import base64
import json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

def main():
    out = ROOT / "results/reference_2022"
    summary = json.loads((out / "summary.json").read_text())
    dispatch = pd.read_csv(out / "dispatch_mw.csv", index_col=0, parse_dates=True)
    annual = dispatch.sum() / 1e6
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.8))
    colors = {"hydro": "#268dad", "combustible": "#d69a54", "other": "#77a96a", "imports": "#8b77b5", "unserved": "#cc5555"}
    capacity = pd.read_csv(ROOT / "data/reference/unsd_2022/statistics.csv").set_index("metric").value
    carriers = ["hydro", "combustible", "other"]
    axes[0].barh(carriers, [capacity[f"capacity_{c}"] for c in carriers], color=[colors[c] for c in carriers])
    axes[0].set(xlabel="Net installed capacity (MW)", title="2022 source capacity")
    names = ["hydro", "combustible", "other", "imports"]
    axes[1].barh(names, annual[names], color=[colors[c] for c in names])
    axes[1].set(xlabel="Annual modelled net electricity (TWh)", title="2022 calibrated dispatch")
    for ax in axes:
        ax.invert_yaxis()
        ax.spines[["top", "right"]].set_visible(False)
    fig.suptitle("Sudan: national reference benchmark", fontsize=16)
    fig.tight_layout()
    fig.savefig(out / "annual_overview.png", dpi=180, bbox_inches="tight")
    fig.savefig(out / "annual_overview.svg", bbox_inches="tight")
    plt.close(fig)
    embedded = base64.b64encode((out / "annual_overview.png").read_bytes()).decode()
    page = f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>PyPSA-Sudan | Reference 2022</title>
<style>body{{font:17px/1.65 system-ui,sans-serif;color:#173347;background:#f1f5f6;max-width:1050px;margin:45px auto;padding:0 24px}}h1{{font-size:42px;line-height:1.15}}article{{background:white;padding:28px;border-radius:14px;margin:22px 0}}.tag{{color:#267b83;font-weight:700}}.metrics{{display:flex;gap:35px;flex-wrap:wrap}}.metrics strong{{display:block;font-size:29px}}img{{width:100%}}a{{color:#126f8b}}code{{background:#edf3f5;padding:3px 6px}}table{{border-collapse:collapse;width:100%}}td,th{{padding:9px;text-align:left;border-bottom:1px solid #dce6e9}}</style></head><body>
<p class="tag">OPEN ELECTRICITY MODELLING · HISTORICAL REFERENCE</p><h1>PyPSA-Sudan<br>Reference year 2022</h1>
<p>2022 is the latest year in the current UNSD Electricity Profiles edition with Sudan's headline generation and major generation categories not flagged as UN estimates. It is a defensible starting point, with important data gaps.</p>
<article class="metrics"><div><strong>4,209 MW</strong>Net installed capacity</div><div><strong>16.771 TWh</strong>Source gross generation</div><div><strong>8,760 hours</strong>Full-year model</div><div><strong>1 national bus</strong>Aggregate benchmark</div></article>
<article><h2>What has been solved</h2><p>Fixed domestic capacity, an annual hydro budget and hourly economic dispatch. Imports and the aggregate “Other” category have flat profiles. Domestic dispatch sums to <b>{summary['net_generation_mwh']/1e6:.3f} TWh net</b>; imports supply <b>{summary['imports_mwh']/1e6:.3f} TWh</b>. Consumption and system losses are accounted for separately.</p>
<img alt="2022 source net capacity and calibrated annual model net generation by category" src="data:image/png;base64,{embedded}">
<p><b>Annual agreement is calibration, not independent validation.</b> The hourly allocation is synthetic; hydro may move freely between months within its annual energy budget, so its timing can be arbitrary. The zero-shortage result is conditional on supplied-energy demand, full installed availability and unrestricted transfers; it does not establish historical reliability.</p></article>
<article><h2>How reliable are the inputs?</h2><table><tr><th>Input</th><th>Status</th></tr><tr><td>National generation, hydro, combustible capacity, imports</td><td>UNSD 2022, not flagged as estimates; not independently verified</td></tr><tr><td>Consumption; Other capacity</td><td>UNSD estimates, flags preserved</td></tr><tr><td>Hourly shape, imports timing, costs, own-use allocation</td><td>Explicit modelling assumptions</td></tr><tr><td>2022 plants, topology, ratings, outages, monthly hydro</td><td>Still needed for the regional research model</td></tr></table></article>
<article><h2>Run and inspect</h2><p><code>conda activate pypsa</code><br><code>python run_model.py</code><br><code>python scripts/make_reference_report.py</code><br><code>python -m pytest -q</code></p><p><a href="docs/REFERENCE_YEAR_2022.md">Year selection and accounting method</a> · <a href="results/reference_2022/summary.json">Solved totals</a> · <a href="data/reference/unsd_2022/statistics.csv">Source statistics</a> · <a href="https://github.com/Elgenied/pypsa-sudan/tree/main/sudan-starter">Public code</a></p></article>
<article><h2>Regional model and publication</h2><p>The earlier 19-region model remains a <a href="LEGACY_2024.html">separate 2024 illustration</a>. Its wartime availability and disabled corridors have not been relabelled as 2022. Next, reconcile a 2022 plant ledger and transmission topology, obtain monthly demand and hydro, and validate against observations that were not used for calibration. See the <a href="docs/PUBLICATION_ROADMAP.md">publication roadmap</a>.</p></article>
<p>Sources: <a href="https://unstats.un.org/unsd/energystats/pubs/eprofiles/2023/prt.pdf#page=30">UNSD Electricity Profiles 2023, Sudan, printed p.196</a> · <a href="https://unstats.un.org/unsd/energystats/pubs/eprofiles/2023/04.pdf">Estimate flags</a>. Research checked 5 September 2026.</p></body></html>'''
    (ROOT / "START_HERE.html").write_text(page, encoding="utf-8")

if __name__ == "__main__":
    main()
