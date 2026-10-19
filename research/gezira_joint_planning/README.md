# Section 14 — Gezira joint grid, solar and battery planning

Open `Sudan_Gezira_Joint_Planning.ipynb` (editable, executed notebook) or `Sudan_Gezira_Joint_Planning.html` (reading copy). This is a separate continuation of sections 12–13 in the system-cost notebook.

The controlled experiment keeps all six Gezira zones, 2022 weather, demand proxies, cost coefficients, losses and recovery conditions. It jointly optimizes grid-connected PV, battery energy, converter power and hourly national imports. National generation and transfers respond in the same model. Other regional zones and selected backbone repairs remain fixed at section 13. Mini-grid and standalone alternatives retain their independently optimized hourly schedules and full lifecycle cost.

Four full-year cases compare selective/restored recovery and fixed/free Gezira service choices. Outside-zone choices, repairs and national generation investment are not reoptimized. Results are conditional on these boundaries and do not establish an unrestricted regional optimum, observed access, or a surveyed construction plan.

Run from the repository root in the `pypsa` environment:

```powershell
python research/gezira_joint_planning/model.py
python research/gezira_joint_planning/check.py
python research/gezira_joint_planning/analysis.py
python research/gezira_joint_planning/build_notebook.py --execute
```

- `model.py`: sizing, binary grid/off-grid decisions, national dispatch and case fingerprints.
- `check.py`: independent saved-output balances, storage, losses, outage, capacity, reference-boundary and lifecycle-cost checks.
- `analysis.py`: before/after maps, capacity and cost comparisons, hourly physical supply plots.
- `results/`: per-case networks, choices, summaries, solver logs, checks, aggregate comparison tables and figures.
- `build_notebook.py`: rebuilds and optionally executes the separate notebook; the notebook itself reads saved results by default, with an explicit rebuild switch.

Input provenance and limitations: [regional model](../../docs/REGIONAL_MODEL.md), [system-cost data](../../data/system_costs/README.md), and [section-13 outputs](../system_costs/results/regional_candidate_diagnostic/). Model currency is constant-2025 USD. System annual costs include national background operation and fixed outside-zone portfolios, not only new electrification spending.

## Solver and reproducibility

The three simpler cases use HiGHS 1.12.0. The restored joint-choice case uses the locally available Gurobi 13.0.1 license: HiGHS attempts were slow at the root relaxation. This changes the numerical solver, not the model assumptions or feasible designs. A Gurobi installation and license are needed for that default rebuild. To use the open-source solver for all cases, pass `--solver highs` to `model.py`; allow longer runtime for the restored joint case. Valid cached results are reused regardless of the requested solver, so use a separate clean result directory or move the case directory aside to force a new solve.

Reading the notebook and running the saved-output validation do not require Gurobi. Solver names, options, logs and bounds are retained with each case. CI checks the saved physical outputs and executes the reading notebook; it does not repeat these optimization runs.

## Main findings

| Recovery | Annual system cost before → after (billion USD/year) | Saving (million USD/year) | Gezira grid-labelled connections before → after |
|---|---:|---:|---:|
| Selective | 3.616794 → 3.590524 | 26.270 | 62.6% → 100% |
| Restored | 1.969282 → 1.924300 | 44.982 | 39.9% → 100% |

Both joint-choice cases select grid service in all six Gezira zones. Selective recovery uses no local solar and 1,324.6 MWh nominal batteries; restored recovery uses 244.0 MW solar and 695.2 MWh nominal batteries. These choices are conditional on each scenario's fixed surrounding plan and proxy demand. The result overturns the remaining off-grid Gezira choices under this particular joint-sizing extension; it does not establish an unrestricted national optimum or settlement-level engineering recommendations.
