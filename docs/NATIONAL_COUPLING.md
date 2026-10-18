# Eight-cluster access planning coupled to Sudan's national dispatch

Read **section 11** of [the existing study notebook](../research/system_costs/Sudan_System_Costs.ipynb). This extends the four-cluster demonstration to eight neighbouring Blue Nile atlas clusters, **978 potential connections**, and the existing **19-node, 13-corridor national reference**. It is not yet a national access allocation.

## What changed

The model replaces the 0.15 USD/kWh bulk-supply allowance with the additional cost of dispatching the national fleet. The selected local plan's hourly imports become an additional load at the national Roseires regional bus. National generation limits, schematic transmission limits, fixed imports/other output and annual hydro-energy budgets remain active. There is no shortage generator in the coupled national solves: both existing background demand and additional access demand must be served.

The separate assumed 30 kW background load and hypothetical 150 kW upstream repair in section 10 are removed here. The national demand already provides the background, and its real modelled fleet provides supply. Common-feeder repair, local routes, local equipment and local feeder outages remain explicit. The country fleet is held at the pre-war 2022 reference in all three cases; the cases are **local feeder recovery conditions**, not measured nationwide war damage.

The eight source clusters are selected before optimization using the previous eligibility rule: Blue Nile, 20–500 potential connections, positive area and no detected nightlight, sorted by distance to the Al Kurumuk anchor and geohash. The candidate graph is the union of a geometric minimum spanning tree and each site's two nearest neighbours, giving 11 candidate edges. Lengths are great-circle distances times 1.3. This is a restricted screening graph, not surveyed engineering routes or all possible Sudan routes.

All sites use the existing anchor's NASA POWER weather series; maximum separation is 9.601 km. Each receives 1 kWh per potential connection per day with the same hourly profile. Building counts are potential service points, not verified customer accounts. The source names recur for different geohashes, so results retain the stable IDs.

## Clock, service and boundary

The national prototype used synthetic Sudan-local hours. The access model uses UTC. Its national load series is shifted by two hours with periodic annual wrap, preserving the full annual totals. The last two UTC hours therefore use the first two local-year hours. This is a documented clock alignment of a synthetic profile, not observed chronological demand.

The selected settlements are assumed **additional access demand**, outside the existing national consumer total by construction. Their actual overlap with aggregate measured consumption is unknown. Absence of source nightlight is not proof of disconnection. Neither the atlas proximity column nor the assignment to Roseires identifies an actual usable tie-in. The Roseires bus represents an aggregate regional balance, not an assertion that a 2 km new line connects the study directly to Roseires city. No unverified long-distance route is drawn.

Historical national accounting losses remain fixed with the baseline demand. Additional access incurs the explicit local feeder/route losses (98% efficiency) and local grid distribution loss (10%); no additional national loss multiplier is applied. The reference's national corridors are lossless transport links. This is a screening treatment, not a marginal-loss calculation for the actual transmission network.

Grid-side PV, storage and diesel are offered at a single shared hub, S1. Other nodes can transit supply even if their own service is off-grid. The repairable common feeder uses the original 2.002 km proximity proxy and a 35% new-line component repair rate. No national upstream restoration investment is optimized. All modelled hours must balance; this does not establish N-1, voltage, protection or probabilistic reliability.

## National coupling and the optimality certificate

Let `x` be the 8,760-hour import profile at Roseires and `Q(x)` the minimum national dispatch cost for existing demand plus `x`. The national problem is a linear program with fixed capacities and an unchanged feasible set except for this extra demand. Its optimal bus-balance dual prices provide a supporting lower bound:

`Q(x) - Q(0) >= Q(x_i) - Q(0) + lambda_i · (x - x_i)`.

The local PyPSA mixed-integer master minimizes local lifecycle cost plus an epigraph constrained by these cuts. It chooses service arrangements, candidate routes, common-feeder repair, shared-hub capacities and all hourly local dispatch. Off-grid designs are independent full-year optimized columns; eliminating the more expensive off-grid column is valid because the two alternatives provide identical delivered service and have no shared constraints.

After each master solve, the national model is re-dispatched with its candidate import profile. Local cost plus `Q(x)-Q(0)` is a feasible upper bound. The master MIP's **dual bound**, not merely its incumbent objective, is the lower bound. Further supporting cuts are added if necessary. Completion requires an absolute gap no greater than the larger of **1 USD/year or 0.01%** of the upper bound. The local master targets a 0.005% MIP gap. At most eight iterations are attempted; an uncertified or infeasible run raises an error instead of being marked complete. With this fixed national reference the selected profiles can be checked directly; infeasibility-cut generation is not implemented for arbitrary future inputs.

These bounds apply to the **declared candidate graph, shared-hub architecture, off-grid definitions, fixed national fleet and service scenario**. They do not certify an unrestricted national investment optimum. A numerical charging penalty of 0.001 USD/MWh is included during optimization, recorded and excluded from reported resource costs.

## Economics and interpretation

The objective is incremental annualized access cost: local systems, new shared routes, common-feeder repair, and additional national dispatch cost relative to the same no-access baseline. The pre-existing national operating bill is reported separately; it is not assigned to these 978 connections. Historical sunk national capital is excluded. There is no simultaneous bulk-price charge, synthetic background load or duplicated upstream repair allowance.

Local lifecycle accounting uses the existing 20-year, real 10%, constant-2025-USD ledger with zero tax transfers. The national prototype's illustrative variable costs (hydro 5, main thermal 140, small diesel 220 and imports 80 USD/MWh) are assigned the same scenario price basis, not claimed as inflation-adjusted or observed Sudan fuel costs. Local diesel retains its separate delivered-fuel/maintenance assumptions. Existing imports and unspecified other generation remain fixed at the reference levels; hydro has an annual energy budget, not a validated seasonal reservoir model.

The recovery cases differ only in local repair budgets and feeder outage schedules: constrained 0 USD and local hours 18–23 unavailable, partial 30,000 USD and hours 19–21 unavailable, broad 100,000 USD and no scheduled outage. Budgets constrain repairs only, not all new investment. They are stationary alternatives, not a transition that buys and discards systems in sequence. Section 10 costs are not directly comparable because its sample, background and supply representation differ.

## Files and reproduction

- [Frozen inputs](../data/national_coupling): eight source rows, candidate routes, shared weather, national NetCDF reference, annual reference totals and source hashes.
- [Builder and bounded coupling algorithm](../research/system_costs/coupled_model.py).
- [Independent checks](../research/system_costs/check_coupled.py): local/national balances, service equality, UTC shift, annual hydro limits, binary choices, connectivity, losses, storage, budgets, cost reconstruction and supporting cuts at solved points.
- [Results](../research/system_costs/results/national_coupling): baseline dispatch, each master/coupling iteration, selected designs, costs, convergence bounds, maps and validation.

```bash
python research/system_costs/coupled_model.py
python research/system_costs/check_coupled.py
python research/system_costs/coupled_analysis.py
python research/system_costs/build_notebook.py
python research/system_costs/run_notebook.py --kernel pypsa
```

On a busy machine, `python research/system_costs/run_coupled_extended.py --seconds 3600` resumes the checked completed cases and gives each unfinished local MIP up to an hour. It changes only the solver time allowance, records that override, and keeps the original formulation and gap tolerances. The default builder allows 1,200 seconds per MIP. A time-limited feasible incumbent is not published as a completed optimum.

The extended driver also accepts `--mip-lp-solver hipo` with `highspy[extras]>=1.15`. This changes the linear-programming backend inside the mixed-integer solver, not the model or its tolerances. Install this optional solver in a separate runtime/environment if retaining the original environment is important. The saved `solver_resource_override.json` records the backend, version and time allowance for the resumed run; completed cases retain their original solver logs. The notebook can read and independently check saved results with the original pinned environment.

Hash-verified caches support offline reproduction. Changing model inputs or solver code invalidates the cache. NetCDF exports omit the local custom constraints; recreate them with the builder. The explicit decision tables and convergence files preserve the saved choices and bounds. Run `prepare_coupled.py` only when deliberately refreshing the frozen inputs from the original repository sources.

## Completed run: 18 October 2026

| Local recovery | Grid connections | Mini-grid connections | Standalone connections | Annualized access cost, USD/year | New shared routes, km |
|---|---:|---:|---:|---:|---:|
| Constrained | 0 | 481 | 497 | 313,261 | 0.000 |
| Partial | 677 | 0 | 301 | 295,002 | 2.324 |
| Broad | 880 | 0 | 98 | 244,038 | 4.521 |

All cases deliver 356.97 MWh/year. Broad recovery connects S1–S4 and retains standalone service at S5–S8. Its modelled annual cost is 22.1% below constrained recovery. The national model supplies 300.766 MWh/year of imports to the broad plan; local PV supplies part of its grid-connected demand. The repair expenditure is 16,648.63 USD in both partial and broad cases, so their difference must not be attributed to more repair spending: feeder availability also differs.

All three local masters report a zero MIP gap and converge in one national coupling iteration. National LP numerical tolerances make the saved master lower bound exceed the recomputed upper bound by 0.00055 USD/year (partial) and 0.19771 USD/year (broad); the code accepts at most 0.50 USD/year of such numerical reversal and clips the displayed gap to zero. This is numerical agreement within tolerance, not an exact-arithmetic proof of zero difference. Independent saved-output checks passed for hourly local/national service, storage, capacity, connectivity, budgets and cost reconstruction.

The constrained and partial cases used HiGHS 1.12.0. Broad recovery used HiGHS 1.15.1 with the HiPO LP backend and a 3,600-second limit, completing its local MIP in about 1,563 seconds. The original conda environment was preserved; the alternate solver ran in an isolated runtime.

## Next scale extension

Add further geographically distinct settlement neighbourhoods and connect their imports at appropriate national buses. The same decomposition can coordinate several interfaces, with a vector of hourly dual prices for each bus. Keep full source coverage and exclusions visible. Subsequent national asset rehabilitation/expansion and multi-period asset carry-over require explicit new decision variables; they are not implied by this fixed-fleet coupling. More measured demand can refine the conditional service model later without blocking this progression.

## Method references

The supporting-cut approach follows the decomposition principle introduced by [J. F. Benders, *Partitioning procedures for solving mixed-variables programming problems* (1962)](https://link.springer.com/article/10.1007/BF01386316). The specific formulation and bound calculation above describe this implementation. It is not a claim to reproduce a published Sudan study. Custom variables, constraints and separate export of their solutions follow [PyPSA 1.0.6's custom-constraint interface](https://docs.pypsa.org/v1.0.6/user-guide/optimization/custom-constraints/).
