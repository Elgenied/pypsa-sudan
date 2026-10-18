# Overall plan: where should Sudan connect, rebuild or supply locally?

[Start here](../README.md) · [Evidence and missing inputs](EVIDENCE_AND_GAPS.md) · [Data collection](../data/README.md)

## The question and intended output

The current geographic scope is [the northern–central regional study](NORTH_CENTRAL_STUDY.md): Northern, River Nile, Khartoum, Gezira, White Nile and Sennar. Section 12 implements a 36-zone finite-portfolio model covering all 11,268 clusters, with residential allocation/uplift accounting, national dispatch, four hypothetical backbone repairs, policy benchmarks and focused checks. See [what is implemented and what remains assumed](REGIONAL_MODEL.md).

**For a defined recovery horizon and electricity service target, which combination of grid rehabilitation/extension, mini-grids and standalone systems supplies existing and newly served demand in Sudan at the lowest system cost?**

The intended result is a **map of demand clusters and preferred service options**, with connection routes, capacity, costs, households/people served, reliability and uncertainty. Section 12 covers six states with whole-zone service choices, national dispatch and four hypothetical backbone repairs. Counts are potential building connections, not observed households or newly connected customers. Section 11 retains the eight-cluster shared-route demonstration. Section 10 retains the four-cluster demonstration; section 9 retains the 18-state independent sample. A country-wide allocation map, surveyed routes and a national rehabilitation investment plan do not yet exist.

The 2022 system is a pre-war reference. Recovery scenarios transform that reference into alternative starting conditions; they do not imply a known date for the end of the war. A five- or ten-year recovery horizon can be an explicit study assumption, with calendar dates assigned when the scenario is defined.

## The study from top to bottom

```mermaid
flowchart TD
    A[Define recovery horizon, access targets and service quality] --> B[Locate people, settlements, businesses and critical loads]
    B --> C[Map existing and repairable grid assets and candidate routes]
    C --> D[Define grid, mini-grid and standalone options with comparable costs]
    D --> E[Choose investments and check hourly supply with PyPSA]
    E --> F[Map preferred options, costs, reliability and uncertainty]
    F --> G[Validate pilot cases and test sensitivity before national conclusions]
```

Two scales must connect: the **national/regional electricity system** and **local settlement access**. The current 19-node model represents the first approximately. The [DRE settlement notebook](../research/dre_atlas_2025/Sudan_DRE_Settlements.ipynb) now provides 33,891 georeferenced clusters and low-service demand estimates; viable routes and verified access remain to be established. The older locality table is contextual evidence at a different scale.

## What each option means

| Primary service option | Assets/costs to include | Questions that can change the result |
|---|---|---|
| **Grid rehabilitation or extension** | Repairs, upstream supply/reinforcement where needed, route construction, transformers, distribution, connections, losses and operation | Is the nearest line usable with enough capacity? Is another route preferable? Can settlements share a trunk route? |
| **Mini-grid** | Local generation, storage/backup, fuel delivery, shared distribution, connections and replacements | Does settlement density justify distribution? Can it meet evening, seasonal and productive loads? |
| **Standalone supply** | Household/facility equipment, batteries, maintenance/replacement and delivery; no shared settlement distribution | What appliances, peak power and service hours can it support? Do productive loads need a separate solution? |

A mini-grid has its own local network. Standalone means separate household/facility systems. Grid-connected places may also use local PV or batteries. Classification describes the primary service arrangement without banning hybrid supply or later grid connection.

Do not assign an option in advance because a district is remote, populous or sunny. These characteristics affect feasibility/costs; the comparison determines the result. Section 10 reports conditional choices for four named source clusters; these do not establish district-wide recommendations.

## Can PyPSA do this?

**Yes, as the energy-system optimization engine in an explicitly designed spatial planning workflow.** PyPSA supports investment in generation, storage and network capacity, given candidate assets and limits. See [capacity constraints for the installed PyPSA 1.0.6](https://docs.pypsa.org/v1.0.6/user-guide/optimization/capacity-limits/).

Settlement technology choices, route activation, repair decisions and connection charges are additional planning logic. PyPSA's underlying optimization model can be extended with custom variables and constraints; loading the present network will not automatically generate an electrification map. See [PyPSA 1.0.6 custom constraints](https://docs.pypsa.org/v1.0.6/user-guide/optimization/custom-constraints/).

I recommend a **GIS and demand layer feeding PyPSA**, with an explicit option-selection layer. [OnSSET](https://onsset.readthedocs.io/en/latest/) is an established geospatial electrification tool comparing grid extension, mini-grid and standalone options. It is a methodological reference or possible linked tool, **not currently installed or integrated here**. Coupling it to PyPSA would require designed data exchanges and consistency checks.

| Layer | Responsibility | Proposed implementation |
|---|---|---|
| **Spatial evidence** | Settlements, access, population, routes, terrain and resources | GIS processing and a documented demand-cluster table |
| **Option selection** | Service arrangement per settlement; route repair/build decisions | Explicit pilot comparison first; then discrete choices with shared-route costs or a carefully linked geospatial model |
| **Energy and capacity** | Generation, storage, imports, transfers and hourly adequacy | PyPSA investment/dispatch model extending the fixed-capacity prototype |
| **Evaluation** | Access, reliability, costs, sequencing and uncertainty | Reproducible scenario tables, maps and validation sections |

Section 12 extends national dispatch coupling to six states and selects local portfolios and four assumed backbone repairs. National generation expansion, asset carry-over and investment sequencing remain proposed work. The finer shared-route formulation in section 11 remains a supporting local demonstration.

## A fair economic comparison

Compare feasible options over the **same service specification, horizon and cost basis**. Minimize discounted lifecycle system cost, including investments/repairs, operation, fuel and replacements, subject to reliability requirements. Historical sunk construction costs should not be charged again as new investment. Tariffs and subsidies are not substitutes for economic resource costs.

Grid options must include upstream supply and connections; mini-grids must include distribution; standalone systems must meet assigned service requirements. Comparing a small solar-home package against full grid service on price alone answers the wrong question. If access tiers differ, make them explicit scenarios rather than silently reducing demand for the cheapest option.

For the pilot, enumerate complete candidate service arrangements and optimize their sizes/operation. Shared routes and upstream constraints make settlements interdependent at national scale. A per-settlement cheapest-option screen alone does not establish a global least-cost plan.

An integrated formulation can add one primary service choice per cluster and period, route-build/repair variables, capacity and operating constraints. Charge fixed costs when options are chosen: a cheap fractional `Link` without activation costs can otherwise produce unrealistic extensions. Tie flows, existing assets and local generation to those choices. Explicitly export and check custom variables and constraints.

A staged approach can iterate local choices with regional supply/network costs. If used, document its algorithm and convergence and benchmark it against a small jointly optimized case; do not call an unverified screen a global optimum. Planning results also do not replace detailed distribution design or protection studies.

## Milestones and completion criteria

| Stage | Deliverable | Complete when | Status |
|---|---|---|---|
| **0. Make the project readable** | Project map, evidence register and notebook guides | Evidence, calibrated results, assumptions and proposed work are visibly distinguished | **Available** |
| **1. Prepare reference and pilot inputs** | Reconciled 2022 fleet; hydro-seasonality upgrade; mapped settlement sample; service and cost tables | Years/definitions/units agree; unknowns have bounds; assets and demand are not double counted | **In progress: DRE and full-scope cost accounting available; cost quotations, routes and service inputs still need validation** |
| **2. Demonstrate a fair comparison** | Representative clusters with grid, mini-grid and standalone alternatives | Feasible options meet service targets; costs reconcile; limiting cases behave plausibly; shared routes and upstream assumptions are exposed | **Three-cluster hourly prototype available; field inputs and engineering validation remain** |
| **3. Couple access and regional supply** | Repair, capacity, network and connection decisions | Balances, service, capacity and budgets pass; small cases are checked independently; screening is distinguished from joint optimization | **Six states coupled to national fixed-fleet dispatch; four hypothetical backbone investments; finite local library and assumed network** |
| **4. Scale and stress-test** | Regional/national maps across recovery, demand, fuel, hydro, cost and finance cases | Robust/uncertain choices are visible; chronological storage and seasonal adequacy are checked; spatial coverage is reported | **36-zone study plus 48-zone, demand and fuel checks available; multi-year weather and broader design alternatives remain** |
| **5. Paper release** | Archived data/version, methods, validation and reproducible notebook | Claims match evidence; holdout/local checks, uncertainty, limitations and source rights are documented | **Planned** |

Choose pilot clusters from the DRE atlas after reviewing actual locations and coverage. Near-grid, dense remote and dispersed rural are useful **case types**, not conclusions about named regions. The source grid-distance column is straight-line proximity to mixed/unknown-voltage grid data, not a verified route. The 2020–2022 conflict categories are historical exposure, not current safety. Synthetic cases can test software but must be labelled and cannot validate geographic recommendations.

## Results for the paper

- Preferred option by cluster, including alternatives that are nearly as cheap.
- Households/people served and critical/productive loads, with a stated service standard.
- Investment and lifecycle costs; cost per connection and delivered energy with clear denominators.
- Repairs, network kilometres, generation/storage additions and timing.
- Reliability, fuel/import dependence and emissions where supported.
- Choices stable across uncertainty, and locations needing better evidence.

The immediate direction is to strengthen the **implemented six-state regional study**: improve weather coverage, broaden fixed local candidate designs, and replace consequential route/tie-in and repair allowances with evidence. Section 12 includes the national background operating bill, whereas section 11 uses incremental dispatch cost; their totals must not be compared directly. See [the regional formulation and scope](REGIONAL_MODEL.md). Measured settlement demand is not a prerequisite for this conditional study.

The [system-cost notebook](../research/system_costs/Sudan_System_Costs.ipynb) contains both the accounting layer and an **18-run hourly pilot** in section 7. It selects three real DRE clusters, retrieves 2022 NASA POWER weather, matches assumed delivered service and optimizes capacities with lifecycle costs. Numerical feasibility and cost reconciliation pass under those assumptions. Stage 2 still needs field-verified service points/loads, routes, scoped quotations, distribution engineering and multi-year weather checks. The four earlier 100-home budgets remain synthetic examples and all USD prices remain provisional.

**Section 8 now implements the next uncertainty milestone:** ten single-input experiments, eight designed joint scenarios per cluster, conditional MV route thresholds and refined mini-grid/standalone demand crossing brackets. Prices, demand, outage schedules and financing remain analyst scenarios, not probability distributions. Capacities are resized for each scenario; the reported architecture cost penalty is not the regret of a fixed investment. Use the resulting decision margins to prioritize load evidence, usable tie-ins/routes and comparable supplier quotations. See the [experiment design and limits](../data/electrification_uncertainty/README.md).

**Section 9 continues using available data:** one deterministic small cluster per state, source building-demand proxies plus 1/2 kWh-per-connection service targets, location-specific 2022 weather and 168 hourly optimizations. Grid is conditionally assessed only within a declared 50 km line-proximity screen; it is not assessed at the other eight sites. Point maps show choices among considered alternatives, not state-wide technology allocation. This is a defensible scoped scenario experiment, not a validated national plan. [Spatial experiment design](../data/spatial_proxy_study/README.md).

The national 2022 pies show capacity or dispatch. Section 12 pies show potential building connections assigned to each service arrangement, by state and recovery condition. There is still no measured post-war damage inventory or country-wide access allocation. A later scope extension could add national generation expansion and asset carry-over between periods. Do not extrapolate sample budgets or the six-state total to all Sudan.
