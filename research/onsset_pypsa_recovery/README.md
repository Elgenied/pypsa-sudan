# Sudan settlement recovery screen: OnSSET + PyPSA

**Open [Sudan_OnSSET_PyPSA_Recovery.ipynb](Sudan_OnSSET_PyPSA_Recovery.ipynb) first.** It contains the saved maps, state charts, scenario definitions, checks and interpretation. [HTML reading copy](Sudan_OnSSET_PyPSA_Recovery.html).

This is the new, active research direction: OnSSET's `Technology.get_lcoe` ranks grid connection, solar-battery mini-grid and standalone systems for 11,268 DRE atlas settlements in Northern, River Nile, Khartoum, Gezira, White Nile and Sennar. The completed [PyPSA regional joint study](../regional_joint_study/README.md) supplies three recovery-case definitions, hourly national dispatch results and corridor repair selections. This is a **one-way linkage**, not a simultaneous OnSSET–PyPSA optimum. National PyPSA costs must not be added to the OnSSET screening totals because their scopes overlap.

## Reproduce

```powershell
conda run -n pypsa python research/onsset_pypsa_recovery/run.py
conda run -n pypsa python research/onsset_pypsa_recovery/build_notebook.py
```

`run.py` fetches upstream OnSSET commit `486c26039ecbf8614d68da90c7b4968b2f4a5b13` into an ignored local `.cache/onsset` directory using Git. It does not modify the Conda environment. Required Python packages are already available in the user's `pypsa` environment: pandas, numpy, scipy, geopandas, shapely, numba, geojson, matplotlib, nbformat, nbclient, nbconvert. The script has a narrow compatibility wrapper around an upstream OnSSET scalar-zero T&D result for vectorized standalone systems. OnSSET's cost calculation otherwise runs unchanged.

## Exactly what this run means

- **Population** is VIDA/GHSL modeled; **potential connections** are buildings ≥15 m², not verified households or meters.
- The atlas's synthetic low-service daily demand is raised to at least 1 kWh/day per potential connection. No observed settlement load curve is available.
- An atlas line within 50 km is a *candidate* grid connection. Line voltage, condition, feeder routing and spare capacity are unverified. Distance is a lower-bound proxy for an actual route.
- Grid supply is priced at the existing cost ledger's $0.15/kWh planning assumption. Illustrative outage fractions equal the previous PyPSA cases' assumed local outage hours divided by 24; displaced energy is assigned a $0.45/kWh reliable-backup cost. This is not an hourly reliability optimization.
- OnSSET mini-grid and standalone options are simplified firm-equivalent PV/battery capital packages ($3,000/kW and $4,000/kW respectively), with explicit capacity-factor proxies. Their storage duration, diesel use, hourly adequacy and security cost are **not** optimized in this screen. The earlier hourly PyPSA regional portfolios provide a separate comparison.
- The `restricted`, `selective` and `restored` corridor repair sets come from completed PyPSA mixed-policy cases. Repair costs are displayed separately, not spread over settlement LCOEs. The screen therefore cannot prove that a corridor repair is cost-effective.
- Atlas security labels come from 2020–22 conflict data. They are shown as context and never treated as current access safety or asset-damage measurements.

The results answer: **how do settlement rankings move under three specified recovery assumptions?** They do not yet answer which actual settlement should receive a project. The [evidence and gaps](../../docs/EVIDENCE_AND_GAPS.md) and [new workflow guide](../../docs/WORKSPACE_GUIDE.md) state what is needed for that claim.

## Files

| File | Role |
|---|---|
| `run.py` | Fetch pinned OnSSET, read atlas and PyPSA case register, calculate LCOEs and classifications, check outputs |
| `build_notebook.py` | Rebuild executed notebook and HTML from the saved run |
| `results/settlement_screen.csv.gz` | One row per settlement and condition, with option LCOEs, capacities and chosen mode |
| `results/state_summary.csv` | Choice totals by state and condition |
| `results/pypsa_case_register.csv` | PyPSA case IDs, assumed outages, repairs and separate system costs |
| `results/manifest.json` | Source/model version and validity flags |

The code intentionally keeps the original notebooks and PyPSA outputs in place so their results remain reproducible; the [workspace guide](../../docs/WORKSPACE_GUIDE.md) gives one clear reading order.
