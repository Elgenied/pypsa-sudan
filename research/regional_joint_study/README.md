# Full six-state joint recovery study

**Status: all 12 cases completed and validated.** Open the [final executed notebook](Sudan_Regional_Joint_Study.ipynb) or [HTML reading copy](Sudan_Regional_Joint_Study.html). This is the national/backbone supply reference for the [active OnSSET–PyPSA settlement screen](../onsset_pypsa_recovery/README.md). The interim six-case notebook below is a frozen historical snapshot; use the final notebook for results.

**Scope:** Northern, River Nile, Khartoum, Gezira, White Nile and Sennar; all 11,268 source clusters and 10,078,666 potential building connections. These are not verified households or counts of customers needing new connections.

**Interim archive:** [six-case notebook](interim_6_cases/Sudan_Regional_Interim.ipynb) and [HTML](interim_6_cases/Sudan_Regional_Interim.html). This frozen snapshot covers restricted and selective recovery only. The final notebook above covers restored recovery and the focused checks too.

This is the full-region continuation of the separate Gezira experiment. Grid-connected equipment and permitted corridor repairs are selected together with national hourly dispatch. Independent mini-grid and standalone alternatives retain their own least-cost full-year designs; the fuel check reoptimizes mini-grids at the changed fuel price.

## Run without an active chat

From the repository root in the `pypsa` environment:

```powershell
python research/regional_joint_study/run_study.py
```

Alternatively use `run_background.ps1` in this directory. The driver executes normal local Python processes and **makes no language-model/API calls**. It uses one solver job at a time and four solver threads. Completed cases are cached using input/output hashes. Rerun the same command to resume. An operating-system lock prevents duplicate drivers and is released if the process exits or crashes.

Read `RUN_STATUS.html` for a self-refreshing progress page, `STATUS.json` for structured state, and `logs/` for case logs. A case counts as completed only after investment optimization, a separate fixed-investment 8,760-hour dispatch replay, and independent saved-output validation. A failed or timed-out solve stops the batch and is explicitly reported. A solver job can run for up to two hours per phase; actual runtime depends on the case and competing local jobs. No claim of a completed study should be made until `STATUS.json` says `complete` and `results/validation.json` passes all 12 cases.

The default is Gurobi, requiring a valid installation/license. `--solver highs` uses the open-source alternative. It may take substantially longer on these formulations. Cached results are reused regardless of solver choice; move a case folder aside to force a fresh solve. Read-only notebook execution and saved-output checks do not require Gurobi.

Optional driver arguments: `--mirror PATH` copies progress and completed results to another study folder; `--publish` commits this study directory and pushes the current `main` branch only after all cases, checks and notebook generation finish. Publication is deferred if unrelated files are staged or Git rejects the push; a `publication_error` is recorded without discarding completed research outputs. Use publication only from the Git checkout, not a plain Desktop copy. The background PowerShell helper exposes these as `-Mirror PATH` and `-Publish`.

## Fixed experiment list

| Cases | Purpose |
|---|---|
| Three recovery conditions × mixed / grid-led / decentralized-first | Nine main comparisons at identical service targets within each recovery condition |
| Selective mixed, 48 zones | Spatial-resolution check preserving source coverage and bus-level demand |
| Selective mixed, residential service +20% | One demand check, with equipment resized |
| Selective mixed, fuel prices +25% | One fuel check, with local mini-grids reoptimized |

Restricted recovery prohibits candidate corridor repairs and imposes local grid outages during 18:00–23:00; selective recovery selects repairs within $45 million and imposes 19:00–21:00 outages; restored recovery requires all four candidate repairs and has no scheduled local outage. The repair budget excludes local systems. The mixed case chooses grid versus the cheaper independent off-grid design. Grid-led permits local solar and batteries; decentralized-first forbids regional grid service while preserving background national demand.

## Outputs

Once all cases pass, `report.py` automatically generates:

- `Sudan_Regional_Joint_Study.ipynb`: executed, separate research notebook.
- `Sudan_Regional_Joint_Study.html`: reading copy with regional maps, state pies, costs, repairs, hourly supply and robustness checks.
- `results/summary.csv`, `state_results.csv`, `all_choices.csv`, `all_repairs.csv`, `zone_energy.csv`, `robustness.csv` and `findings.json`.
- Per-case NetCDF investment/replay networks, selected designs, full costs, solver bounds/logs, hashes and validation records.

The notebook does not rerun optimization when opened. Rebuild figures/notebook with `python research/regional_joint_study/report.py`. Recheck saved results with `python research/regional_joint_study/check.py`.

## Interpretation

This is a full-year, whole-zone, scenario-based planning study using the available evidence. It is not a reconstruction of measured current access or surveyed war damage. National plant capacities, external demand, repairable corridor definitions and capacity limits are inherited; new national generation investment, repair timing, feeder voltage and shared inter-cluster routing are outside this experiment. The 2022 weather year and historical monthly hydro shapes are explicit assumptions. Grid transformer/route quantities remain cost proxies and are not redesigned against the optimized charging peak.

Annual costs include national background operation; they are not simply access-program budgets. Initial local-and-repair spending excludes sunk national generation. Potential connections must not be relabelled as households. Source dates and provenance are retained in [regional inputs](../../data/regional_model/), [scope](../../docs/NORTH_CENTRAL_STUDY.md), [model documentation](../../docs/REGIONAL_MODEL.md) and [cost evidence](../../data/system_costs/README.md).
