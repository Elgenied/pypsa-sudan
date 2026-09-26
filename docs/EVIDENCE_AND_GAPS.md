# What we have, what we checked, and what is missing

[Start here](../README.md) · [Study plan](STUDY_PLAN.md) · [Data catalog](../data/README.md)

Status reviewed **26 September 2026**. This page distinguishes evidence quality from successful software execution. For current run status see [GitHub Actions](https://github.com/Elgenied/pypsa-sudan/actions).

## The four labels we use

| Label | Meaning |
|---|---|
| **Extracted / sourced** | Traceable to a document, year and definition; this alone does not establish accuracy or current relevance |
| **Calibrated** | A model matches an input target used to construct it |
| **Numerically checked** | Accounting, bounds or replicated arithmetic passed stated checks |
| **Independently validated** | A result agrees with suitable evidence not used to set or fit that result |

The current notebooks have sourced inputs, calibration and numerical checks. **Neither establishes independent validation of a national post-war electrification plan.**

## Evidence and model inventory

| Topic | Available | Treatment now | Remaining limitation |
|---|---|---|---|
| 2022 national electricity | UNSD net capacity 4,209 MW; net generation 16,031 GWh; imports 882 GWh; consumer electricity 13,261 GWh; losses 3,652 GWh | Calibration anchors embedded in baseline notebook | National accounting does not identify local service quality or unserved demand; some categories are estimates |
| 2022 regional fleet | Historical plant weights reconciled to national net-capacity totals | Assumed regional allocation | Not a verified unit inventory; rental/autoproducer coverage and gross/net basis need reconciliation |
| Plant engineering | 19 unit-group/configuration records with coordinates, fuels, heat rates, O&M and capacities | Historical CSVs, separate from baseline | 2012 vintage; committed projects and replacement configurations require checks; some values conflict |
| Transmission | 13 schematic baseline corridors; historical route/voltage information and 37 planned routes | Baseline MW limits are assumed; historical routes document plans | No complete validated network, ratings, damage or repair costs; voltage is not a MW rating |
| Regional demand | 2011 state-sector consumption; assumed 2022 node shares | Historical data not yet integrated | Historical 15-state geography differs from the 19 regional proxies and modern states |
| Hydro | Annual budget in baseline; monthly characteristics for eight historical configurations | Monthly data available for a future upgrade | Not measured 2022 inflows; gross/net and annual/monthly conflicts; no reservoir model |
| Local access | 131 historical localities, 2008 demographics, 2012 grid status and estimated distances | Starting evidence for spatial work | No locality coordinates in this table; localities are not individual settlements; proximity is not household access |
| Demand projections | Three 2012–2031 scenarios, 60 national scenario-years and 720 monthly records | Published outputs plus partial arithmetic replication | Not actual 2022 or post-war demand; not an optimal investment plan |
| Economic inputs | Historical plant O&M and illustrative baseline marginal costs | Reference values, not a planning cost database | Repairs, connections, distribution, solar, storage, fuel delivery, price basis and financing not established |
| Recovery and service targets | Research design only | No implemented scenario dataset | Damage, restoration time, displacement, critical loads, service standards and horizons need explicit evidence/assumptions |

## What passed, and what that proves

### Notebook A: 2022 system reference

The saved solution is optimal for its stated linear program. [Numerical checks](../results/numerical_checks.csv) cover hourly nodal balance, generator limits, corridor limits and hydro budgets. The maximum nodal residual is approximately **3.6 × 10⁻¹³ MW**; [annual calibration](../results/annual_calibration.csv) matches the constructed targets.

The [sensitivity results](../results/sensitivity_results.csv) show:

- A 20% smaller hydro budget increases modeled combustible generation from about **4,628 to 6,885 GWh**.
- Halving assumed corridor limits produces about **33.7 GWh of modeled shortage**.

These are conditional model responses. Zero baseline shortage does not demonstrate universal access or absence of real outages: unconnected/suppressed demand is not represented. Congestion on a schematic corridor is not evidence that a specific real line should be built.

**Independent validation still needed:** a reconciled fleet and topology; suitable 2022 peak, monthly generation, regional sales or dispatch observations withheld from calibration. Report residuals and scope differences rather than forcing agreement.

### Notebook B: historical evidence and replication

[Ten arithmetic checks](../research/forecasting_2012/results/validation_checks.csv) pass documented rounding tolerances. Sequential loss reconstruction matches 60 annual sent-out-energy entries within **0.872 GWh**. Annual/monthly printed balance arithmetic has been checked where required values exist. The PDF lacks the original forecasting workbook, so this is not a full recreation of its connection forecasting engine.

The [source-issue register](../research/forecasting_2012/results/source_issues.csv) retains:

- Annual versus summed monthly energy differences up to **1,022 GWh**.
- National versus state-table aggregate peak differences up to **237 MW**.
- Differing reserve conventions, missing monthly capacity cells in 2031, hydro reconciliation problems and efficiency conflicts.

Catalog checks establish data integrity. They do not certify forecasts, asset status or post-war applicability. Successful GitHub execution is a reproducibility check, not peer review or independent system validation.

## Prioritized gaps for the electrification question

| Priority | Needed input / decision | Why it matters | Minimum useful next deliverable |
|---|---|---|---|
| **1** | Georeferenced settlements/demand clusters, households, access and productive/critical loads | Defines who is served and demand size/location | Pilot table with coordinates, provenance, date and demand/service ranges |
| **1** | Usable/repairable grid, candidate routes, capacity and condition | Defines feasible connections, not merely nearest distance | Route table with endpoints, length, capacity and repair/extension assumptions |
| **1** | Comparable lifecycle costs | Determines economic choice | One price year/currency; CAPEX, O&M, replacements, fuel, finance, distribution and connections |
| **1** | Service and reliability requirements | Prevents an unfair comparison of a small solar-home system with continuous grid service | Quantity, peak capability, service hours and critical-load/shortage requirements |
| **2** | Renewable profiles/siting limits; seasonal hydro | Determines feasible generation and storage | Documented profiles; final candidates tested against fuller chronology |
| **2** | Recovery scenarios and implementation limits | Changes usable assets, timing and cost | Explicit low/central/high repair and demand assumptions, not an invented damage inventory |
| **2** | Boundary and asset crosswalks | Prevents double counting and wrong spatial assignment | Historical-to-study-area mapping; one record per physical asset/configuration/year |
| **3** | Independent validation and local review | Determines credible paper claims | Holdout comparisons, benchmark pilot cases, sensitivity maps and route/service review |

Missing exact damage records do not prevent scenario analysis. The claim becomes **conditional least-cost choices under documented recovery assumptions**, rather than a verified reconstruction plan.

## Claims today

**Supported:** a reproducible, nationally calibrated regional dispatch prototype; traceable historical datasets; replicated visible arithmetic; documented sensitivity to selected assumptions.

**Not yet supported:** settlement-specific technology choices, universal-access cost, optimal repair priorities, a validated post-war grid map, electrical security certification or treating 2012 projections as observations.

Use the [study plan](STUDY_PLAN.md) to move from these inputs to the intended planning results.
