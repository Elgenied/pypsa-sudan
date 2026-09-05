"""Create offline results viewer and exportable figures from solved CSV outputs."""
from pathlib import Path
import base64
import html
import json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import numpy as np
import pandas as pd
import geopandas as gpd
import plotly.graph_objects as go

ROOT = Path(__file__).resolve().parents[1]
FIG = ROOT / "results/figures"
COLORS = {"hydro": "#2389ac", "oil": "#dd9b53", "coal": "#64748b", "diesel": "#975c41", "import": "#8a70be", "unserved": "#da5353"}
LABELS = {"hydro": "Hydro", "oil": "Oil", "coal": "Coal", "diesel": "Diesel", "import": "Imports", "unserved": "Unmet demand"}


def save(fig, name):
    fig.savefig(FIG / f"{name}.png", dpi=180, bbox_inches="tight", facecolor="white")
    fig.savefig(FIG / f"{name}.svg", bbox_inches="tight", facecolor="white")
    plt.close(fig)


def embed(name):
    data = base64.b64encode((FIG / f"{name}.png").read_bytes()).decode()
    return f'<img alt="{name.replace("_", " ")}" src="data:image/png;base64,{data}">'


def main():
    FIG.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.spines.top": False, "axes.spines.right": False, "axes.titleweight": "bold", "axes.labelcolor": "#334155", "text.color": "#162b3c"})
    comparison = pd.read_csv(ROOT / "results/scenario_comparison.csv")
    if len(comparison) != 6:
        raise ValueError("Run --scenario all before building the comparison report")
    summary = json.loads((ROOT / "results/baseline_2024/summary.json").read_text())
    buses = pd.read_csv(ROOT / "data/curated/buses.csv").set_index("bus")
    links = pd.read_csv(ROOT / "data/curated/corridors.csv")
    plants = pd.read_csv(ROOT / "data/processed/plants_geolocated.csv")
    boundary = gpd.read_file(ROOT / "data/processed/sudan_boundary.geojson")
    historic = gpd.read_file(ROOT / "data/processed/historical_transmission_clipped.geojson")
    fig, ax = plt.subplots(figsize=(11, 10))
    boundary.plot(ax=ax, facecolor="#f6f4ee", edgecolor="#a6aeb5", linewidth=0.9)
    historic[historic.STATUS == "Existing"].plot(ax=ax, color="#c2c8cd", linewidth=0.7, alpha=0.8)
    for row in links.itertuples(index=False):
        a, b = buses.loc[row.bus0], buses.loc[row.bus1]
        ax.plot([a.longitude, b.longitude], [a.latitude, b.latitude], color="#df7551" if not row.baseline_active else "#738ca0", lw=1.5, linestyle="--" if not row.baseline_active else "-", zorder=2)
    colors = {"north": "#2389ac", "south": "#de9d52", "isolated": "#b76d84"}
    offsets = {"Kosti": (-55, -16), "WadMedani": (7, 3), "Sennar": (8, -12), "Gedaref": (9, -12), "Khartoum": (-100, 0), "Kassala": (8, 5), "ElGeneina": (-8, 10), "Nyala": (-14, -17), "Zalingei": (-58, 0), "EnNahud": (8, -12)}
    for name, row in buses.iterrows():
        ax.scatter(row.longitude, row.latitude, s=30 + row.mean_load_mw / 2, c=colors[row.grid_group], edgecolors="white", linewidth=0.9, zorder=3)
        ax.annotate(row.label, (row.longitude, row.latitude), xytext=offsets.get(name, (7, 6)), textcoords="offset points", fontsize=9, zorder=4)
    ax.set_xlim(21.4, 39.4)
    ax.set_ylim(8, 22.7)
    ax.set_xlabel("Longitude (degrees east)")
    ax.set_ylabel("Latitude (degrees north)")
    ax.set_title("Sudan: regional dispatch network", loc="left", fontsize=19, pad=18)
    handles = [Line2D([], [], marker="o", color="none", markerfacecolor=c, label=g.title()) for g, c in colors.items()]
    handles += [Line2D([], [], color="#738ca0", label="Assumed active transfer corridor"), Line2D([], [], color="#df7551", ls="--", label="Disabled; restoration scenario only"), Line2D([], [], color="#c2c8cd", label="Historical GIS geometry (context)")]
    ax.legend(handles=handles, loc="lower right", frameon=True, facecolor="white", fontsize=9)
    fig.text(0.12, 0.025, "Regional points and straight connectors are schematic, not surveyed substations or line routes.\nBoundary: Natural Earth. Historical grid: World Bank/AICD. Operating-state reference: August 2024.", fontsize=9, color="#64748b")
    save(fig, "network_map")

    dispatch = pd.read_csv(ROOT / "results/baseline_2024/dispatch_by_carrier_mw.csv", index_col=0, parse_dates=True)
    demand = pd.read_csv(ROOT / "results/baseline_2024/demand_mw.csv", index_col=0, parse_dates=True).sum(axis=1)
    fig, ax = plt.subplots(figsize=(12, 4.5))
    order = [c for c in COLORS if c in dispatch and dispatch[c].abs().max() > 1e-6]
    ax.stackplot(dispatch.index, *[dispatch[c].clip(lower=0) for c in order], colors=[COLORS[c] for c in order], labels=[LABELS[c] for c in order], alpha=0.95)
    ax.plot(demand.index, demand, color="#1e293b", lw=1, label="Synthetic demand")
    ax.set_ylabel("Power (MW)")
    ax.set_title("Illustrative baseline: seven days of hourly dispatch", loc="left", pad=15)
    ax.legend(ncol=3, loc="upper left", fontsize=9)
    ax.set_ylim(0, demand.max() * 1.28)
    fig.autofmt_xdate()
    save(fig, "baseline_dispatch")

    fig, ax = plt.subplots(figsize=(10, 4.8))
    bars = ax.barh(comparison.scenario.str.replace("_", " "), comparison.unserved_percent, color=["#2389ac", "#d96953", "#dd9b53", "#af849f", "#4aa397", "#8a70be"])
    ax.invert_yaxis()
    for bar, value in zip(bars, comparison.unserved_percent):
        ax.text(value + 0.25, bar.get_y() + bar.get_height() / 2, f"{value:.2f}%", va="center")
    ax.set_xlim(0, comparison.unserved_percent.max() + 4)
    ax.set_xlabel("Unmet modelled energy (% of scenario demand)")
    ax.set_title("Sensitivity to assumptions", loc="left", pad=15)
    fig.text(0.13, -0.01, "Illustrative scenarios, not measured outages. No investment costs or probability weighting.", fontsize=9, color="#64748b")
    save(fig, "scenario_comparison")

    interactive = go.Figure()
    carriers = list(COLORS)
    for i, scenario in enumerate(comparison.scenario):
        df = pd.read_csv(ROOT / f"results/{scenario}/dispatch_by_carrier_mw.csv", index_col=0, parse_dates=True)
        load = pd.read_csv(ROOT / f"results/{scenario}/demand_mw.csv", index_col=0, parse_dates=True).sum(axis=1)
        for c in carriers:
            values = df[c].clip(lower=0) if c in df else np.zeros(len(df))
            interactive.add_trace(go.Scatter(x=df.index, y=values, name=LABELS[c], stackgroup="power", line={"color": COLORS[c], "width": 0.5}, visible=i == 0))
        interactive.add_trace(go.Scatter(x=df.index, y=load, name="Synthetic demand", line={"color": "#172f42", "width": 1.5}, visible=i == 0))
    per_case = len(carriers) + 1
    buttons = [{"label": scenario.replace("_", " "), "method": "update", "args": [{"visible": [j // per_case == i for j in range(len(interactive.data))]}, {"title": f"Hourly dispatch: {scenario.replace('_', ' ')}"}]} for i, scenario in enumerate(comparison.scenario)]
    interactive.update_layout(template="plotly_white", height=480, title="Hourly dispatch: baseline 2024", margin={"t": 95, "b": 50}, yaxis_title="MW", xaxis_title="Model time: Sudan local standard time", hovermode="x unified", legend={"orientation": "h", "y": -0.24}, updatemenus=[{"buttons": buttons, "x": 1, "y": 1.18, "xanchor": "right"}])
    interactive_html = interactive.to_html(full_html=False, include_plotlyjs=True, config={"displaylogo": False, "responsive": True})
    table = comparison[["scenario", "demand_mwh", "served_mwh", "unserved_percent", "operating_cost_usd"]].copy()
    table.columns = ["Scenario", "Demand (MWh)", "Served (MWh)", "Unmet (%)", "Operating cost (USD)"]
    table_html = table.to_html(index=False, float_format=lambda x: f"{x:,.2f}", border=0)
    plant_table = plants[["name", "carrier", "p_nom_mw", "available_mw_2024", "coordinate_quality"]].copy()
    plant_table.columns = ["Plant", "Carrier", "Nameplate MW", "Reported available MW", "Location quality"]
    plant_html = plant_table.to_html(index=False, na_rep="Unquantified; model assumes 50%", border=0)
    qa = [json.loads((ROOT / f"results/{s}/validation.json").read_text()) for s in comparison.scenario]
    worst = max(q["max_nodal_balance_error_mw"] for q in qa)
    report = f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>PyPSA-Sudan | Research starter</title><style>
    *{{box-sizing:border-box}}body{{margin:0;background:#eef2f3;color:#1b3445;font:16px/1.65 system-ui,sans-serif}}main{{max-width:1180px;margin:auto;padding:48px 32px}}header{{background:#163b50;color:white;padding:44px;border-radius:20px}}h1{{font-size:46px;line-height:1.15;margin:12px 0}}h2{{font-size:28px;margin:4px 0 20px}}h3{{font-size:20px}}.eyebrow{{letter-spacing:2px;text-transform:uppercase;font-size:12px;color:#9bd2d9}}.subtitle{{color:#ccdde4;max-width:760px}}section{{background:white;border-radius:16px;padding:30px;margin-top:24px;overflow:hidden}}.note{{padding:18px 22px;background:#fff3dc;border-left:4px solid #dda249;border-radius:7px}}.stats{{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-top:24px}}.stat{{background:white;padding:20px;border-radius:14px}}.number{{font-size:29px;font-weight:700}}.muted,small{{color:#64748b}}img{{max-width:100%;height:auto;display:block;margin:auto}}a{{color:#147b94}}table{{border-collapse:collapse;width:100%;font-size:13px}}th{{text-align:left;background:#edf4f5}}td,th{{padding:10px;border-bottom:1px solid #dce5e8}}.scroll{{overflow:auto}}code{{background:#eef3f5;padding:2px 5px;border-radius:4px}}li{{margin:10px 0}}footer{{padding:25px;color:#64748b;font-size:13px}}@media(max-width:750px){{main{{padding:20px 12px}}header,section{{padding:22px}}h1{{font-size:34px}}.stats{{grid-template-columns:repeat(2,1fr)}}}}
    </style></head><body><main>
    <p><b>Legacy 2024 illustration.</b> <a href="START_HERE.html">Open the default 2022 reference benchmark</a>.</p><header><div class="eyebrow">Open electricity modelling · v0.1.0</div><h1>PyPSA-Sudan</h1><p class="subtitle">A reproducible starting point for studying Sudan's electricity system, with a dated plant inventory, regional dispatch and visible uncertainty.</p><small style="color:#a9c5d1">Research checked 5 September 2026 · Fleet-status reference August 2024 · Independent project</small></header>
    <div class="stats"><div class="stat"><div class="number">19</div>regional buses</div><div class="stat"><div class="number">20</div>plant records</div><div class="stat"><div class="number">3.65 GW</div>documented nameplate</div><div class="stat"><div class="number">168 h</div>per scenario</div></div>
    <section><div class="note"><strong>Research starter, not a verified 2026 reconstruction.</strong> Plant status is anchored to August 2024. Hourly demand, transfer ratings, costs and hydro energy are assumptions. The results cannot be cited as actual outages, market prices or a recommended investment plan.</div><p>The baseline solves a lossless transport model with a northern component, a southern component, seven isolated regional systems, and two import supplies. Red unmet-demand quantities are accounting variables, never physical generation.</p><p><a href="docs/METHODOLOGY.md">Methodology</a> · <a href="docs/PUBLICATION_ROADMAP.md">Publication roadmap</a> · <a href="docs/DATA_SOURCES.md">Data sources</a> · <a href="results/scenario_comparison.csv">Download results CSV</a></p></section>
    <section><h2>The network</h2>{embed('network_map')}<p class="muted">Transfer capacities are user-editable assumptions. Historical GIS was fetched and audited, but its map geometry does not establish present topology, circuit ratings or impedances. Nine plant records use regional location proxies.</p></section>
    <section><h2>Dispatch you can inspect</h2><p>Choose a scenario, hover for hourly values, or click the legend to inspect a carrier. This viewer works offline.</p>{interactive_html}<p class="muted">All model hours carry weight one. The week is not multiplied into an annual reliability estimate. Hydro energy is limited across the week; reservoir inflows and cascades are not represented.</p></section>
    <section><h2>What changes the result?</h2>{embed('scenario_comparison')}<div class="scroll">{table_html}</div><p>Baseline demand is {summary['demand_mwh']/1000:.2f} GWh, with {summary['unserved_percent']:.2f}% unmet. The grid-repair scenario both reconnects the two central corridors and doubles domestic transfer limits. Its effect is therefore a combined intervention, not the isolated value of one line.</p><p class="muted">Costs use assumed USD/MWh inputs. Operating cost excludes the artificial unmet-demand penalty; the optimization objective includes both. Hourly and regional shortage allocation can be non-unique when regions share the same penalty.</p></section>
    <section><h2>Plant inventory</h2><p>Capacities and status: <a href="https://documents1.worldbank.org/curated/en/099080625100525928/pdf/P171810-aceaafc9-7439-4838-974c-81284effd33a.pdf">World Bank 2024 update, Annexes 1–2</a>. Historical coordinates: <a href="https://github.com/wri/global-power-plant-database">WRI Global Power Plant Database</a>, where matched. Nameplate and available MW are different fields.</p><div class="scroll">{plant_html}</div><p class="muted">All marginal costs are assumptions. Setit/Upper Atbara is assigned to the southern component following the report's prose; its annex says North. The disagreement remains open for verification. Rooftop PV, captive generation and unverified newer projects are not quantified in this baseline.</p></section>
    <section><h2>Validation performed</h2><p>All six scenarios reached an optimal solution. Maximum nodal balance error: {worst:.2e} MW. Checks cover generator limits, transfer limits, hydro budgets, local shortage bounds and objective reconstruction. Additional regression tests cover shut-down plants, grid islands, demand normalization and NetCDF reload.</p><p><strong>Numerical validation passes; empirical validation remains outstanding.</strong> No claim is made that synthetic regional demand reproduces observed service. Source tables, input hashes, solver logs and network files accompany each run.</p></section>
    <section><h2>A credible route to a paper</h2><ol><li><strong>Fix the study date and question.</strong> Prefer a validated pre-conflict reference plus dated conflict/recovery scenarios, or obtain a current utility status snapshot.</li><li><strong>Replace demand and grid assumptions.</strong> Secure monthly energy, hourly loads, substation connections, line ratings and outage records.</li><li><strong>Add hydrology and distributed solar.</strong> Build full-year inflow/renewable profiles and test several weather years.</li><li><strong>Validate before drawing policy conclusions.</strong> Compare monthly generation by plant, imports, regional supply and observed outages; retain an independent validation period.</li><li><strong>Measure a contribution.</strong> Compare network repair, distributed solar/storage and fuel restoration with investment costs and uncertainty ranges.</li><li><strong>Release reproducibly.</strong> Publish code, permitted data, a tagged environment and a DOI; contribute verified Sudan-specific corrections to PyPSA-Earth.</li></ol><p>Suggested research question: <em>Which combination of grid restoration and decentralized supply most robustly reduces unserved electricity under uncertainty in hydro, fuel and population displacement?</em> This model supplies the scaffold, not an answer yet.</p></section>
    <footer>Independent PyPSA-based study; no official affiliation implied. Sources retain their own rights. Static figures are available as PNG and SVG in results/figures. See docs/DATA_LICENSES.md before redistributing source files.</footer>
    </main></body></html>'''
    (ROOT / "LEGACY_2024.html").write_text(report, encoding="utf-8")
    print("Created LEGACY_2024.html and PNG/SVG figures")


if __name__ == "__main__":
    main()
