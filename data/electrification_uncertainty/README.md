# Exploratory uncertainty and break-even study

Read **section 8** of the existing [system-cost notebook](../../research/system_costs/Sudan_System_Costs.ipynb). It extends the three-cluster pilot without changing its baseline inputs or stored results.

`design.json` is the editable experiment specification. These are **analyst-selected test ranges**, not observed Sudan price distributions, probabilities, confidence intervals or evidence of current infrastructure damage. The discount-rate, fuel and grid-price endpoints reuse the existing cost framework; the other endpoints are explicit exploratory choices. All USD quantities retain the constant-2025-USD basis. Nominal exchange rates and inflation are not mixed with real discount rates.

## Experiment

- One input at a time: daily service demand (0.5–3 kWh per point), PV equipment cost (0.7–1.3 times central), battery-module cost (0.6–1.4), real discount rate (6–18%), delivered diesel (1–3 USD/litre), bulk grid supply (0.08–0.30 USD/kWh), outages (0/3/6/9 hours/day beginning 18:00 local and wrapping midnight), imported standalone hardware markup (1–1.5), installed MV unit cost (0.6–1.6) and LV length (0.7–1.5).
- Every comparison preserves the same delivered hourly service across architectures. Demand changes scale the existing profile; they do not simulate measured diversity, productive use or seasonal behaviour.
- Eight joint corners per site combine demand (0.5 or 2 kWh/day), a lower/higher PV-and-battery cost bundle and grid outage duration (0 or 6 hours/day). Finance, fuel, bulk supply and routes remain central in these joint cases. The paired hardware costs are a deliberate bundle, not an estimated correlation. The corners do not cover all possible interactions.
- Each operationally relevant case sizes capacity and dispatches all 8,760 hours using the unchanged PyPSA pilot engine. Identical problems, including modes unaffected by a parameter, reuse content-checked solutions. Separate worker processes prevent scenario assumptions leaking between runs. Baseline files are not overwritten.
- MV cost and LV length only change fixed infrastructure expenditure in this model. Their sensitivity is therefore an **exact lifecycle-ledger adjustment**, not a claim that these cases were separately dispatched. Constant losses, fixed tie-in capacity, and no length-dependent voltage constraints explain this separability. The exported investment, operating cost, NPC and annual cost all include the adjustment.

## Break-even definitions

**MV route:** for each cluster and outage schedule, write grid annual cost as `C_grid(L) = C_grid(0) + a_MV * L`. The coefficient includes installed line cost, maintenance, development allowances, replacements/retirement where applicable, and the existing lifecycle accounting. Solve `L* = (C_best_offgrid - C_grid(0)) / a_MV`. A negative result is reported as no nonnegative crossing: grid already costs more at zero new MV length. Route kilometres are not straight-line distance. The existing pilot route remains 1.3 times atlas proximity. The alternative length is hypothetical and holds LV layout and all electrical assumptions constant. This is not a feasible-route survey or evidence that a nearby line is usable.

**Demand:** locate every sign change between tested demand points for mini-grid cost minus standalone cost. Refine each crossing with full-year solves to a bracket no wider than 0.025 kWh per service point per day. This is a pairwise comparison; the grid could still be cheaper. No uniqueness or absence of crossings between untested points is claimed.

**Outages:** report crossings between the tested integer-hour schedules. No fractional-hour threshold is interpolated. Increasing duration removes a nested set of hours from upstream availability; this is not an observed wartime outage process.

## Stability and data collection

Report the number of the eight joint scenarios in which an architecture is cheapest or within 5% of cheapest. **Counts are not probabilities.** A range across these cases is not a statistical interval. The 5% near-tie criterion is an analyst choice.

The reported architecture regret is its re-optimized cost minus the cheapest re-optimized architecture in the same scenario. Capacities adapt in every case. This is an **adaptive-capacity comparison**, not the regret or reliability of a single fixed design chosen before uncertainty is revealed; it is not robust or stochastic investment optimization.

Data priorities identify assumptions whose tested ranges change the preferred option. The ranking depends on those ranges and does not estimate formal expected value of information. It guides requests for load evidence, comparable quotations, tie-in availability and routing checks; it does not replace them.

## Limits carried forward

The same three illustrative clusters, 2022 horizontal-array weather approximation, assumed household profile, geometric LV routes, fixed 80 kW grid tie-in, continuous capacities and constant distribution losses remain. Mini-grid diesel is still capped at 20% of delivered annual demand. Battery life is fixed at the central eight-year assumption in this experiment. These restrictions can affect threshold values and the strength of a price response. No national extrapolation, shared feeder optimization, multi-year weather validation, dated damage inventory or real restoration sequence is introduced. Results are lifecycle project-cost comparisons retaining the framework's assumed tax allowances, not a tax-excluded national welfare optimum.

## Reproduce

From the repository root in the `pypsa` environment:

```shell
python research/system_costs/uncertainty_model.py
python research/system_costs/check_uncertainty.py
python research/system_costs/uncertainty_analysis.py
python research/system_costs/build_notebook.py
python research/system_costs/run_notebook.py --kernel pypsa
```

Normally the notebook verifies and reuses checked outputs. `uncertainty_model.py --force` rebuilds experiment tables, still reusing identical verified individual solutions. To explicitly resolve one case, preserve/move its `results/uncertainty/cases/<case_id>/case.json` marker before running. Changing model code or input hashes invalidates individual caches automatically. Altering central pilot/cost assumptions also requires updating experiment centres in `design.json` to match the intended baseline.

`results/uncertainty/` holds experiment tables, thresholds, figures, validation and the manifest. Each `cases/<case_id>/` holds the precise effective assumptions, provenance hashes, complete hourly solution and numerical residuals. `assumptions_json` identifies the cached operating problem; `scenario_assumptions_json` describes the full comparison, including any exact network-cost adjustment. The pilot engine's `demand_multiplier` is relative to the temporarily selected daily-demand setting; use the scenario specification and `annual_delivered_kWh` for cross-case demand.

Independent checks reconstruct hourly balances, storage chronology, capacity limits, outage restrictions, matched service and full lifecycle costs. They check that tighter supply/higher purchase costs cannot reduce minimized annual cost, and verify threshold arithmetic/brackets. They establish numerical consistency, **not field validity**.
