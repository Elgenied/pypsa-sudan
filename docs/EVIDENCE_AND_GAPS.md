# What we have, what we checked, and what is missing

[Start here](../README.md) · [Study plan](STUDY_PLAN.md) · [Data catalog](../data/README.md)

Evidence status updated **17 October 2026**; model results below retain their previous runs. This page distinguishes evidence quality from successful software execution. For current run status see [GitHub Actions](https://github.com/Elgenied/pypsa-sudan/actions).

## The four labels we use

| Label | Meaning |
|---|---|
| **Extracted / sourced** | Traceable to a document, year and definition; this alone does not establish accuracy or current relevance |
| **Calibrated** | A model matches an input target used to construct it |
| **Numerically checked** | Accounting, bounds or replicated arithmetic passed stated checks |
| **Independently validated** | A result agrees with suitable evidence not used to set or fit that result |

The current notebooks have sourced inputs, calibration and numerical checks. **These do not establish independent validation of a national post-war electrification plan.**

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
| Spatial settlements | World Bank/VIDA DRE release: 33,891 georeferenced clusters; potential building connections, modeled demand, polygons, roads, PV, distance to grid and nightlights | Source files checked and mapped in [Notebook C](../research/dre_atlas_2025/Sudan_DRE_Settlements.ipynb) | Mixed layer vintages; no metered access, feasible routes, post-war line status or hourly loads |
| Historical conflict exposure | DRE 2020–2022 ACLED fatality buffers at 25 and 50 km | Category formula reproduced for all 33,891 settlements | **Not a current security or damage assessment** |
| Demand projections | Three 2012–2031 scenarios, 60 national scenario-years and 720 monthly records | Published outputs plus partial arithmetic replication | Not actual 2022 or post-war demand; not an optimal investment plan |
| Economic inputs | Historical O&M; dated Sudan quotations and [full-scope system-cost accounting](../data/system_costs/README.md) with four illustrative designs | Original evidence separate from provisional USD assumptions; no automatic replacement of baseline costs | Comparable quotations, dated FX/price normalization, repair and distribution prices, battery specifications, finance and feasible supply still needed |
| Recovery and service targets | August 2024 status for 20 plant records; five electricity-related NDC measures; programme outputs and qualitative mechanisms | Dated evidence available; no implemented recovery optimization | Asset repair cost/time, present condition, hourly service requirements and demand displacement still require explicit evidence/assumptions |

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

### Notebook C: spatial source checks

The public CSV and GeoJSON have identical **33,891 unique `geohash` IDs** and matching attribute values. The original geometries are valid; the repository stores 100 m simplified display polygons and the full non-geometry attributes. Recalculating `1.1 × large + 0.65 × medium + 0.335 × small` matches every demand row within **0.05 kWh/day** of one-decimal source rounding. The 2020–2022 25/50 km fatality rule exactly reproduces every historical risk label. The [validation report](../research/dre_atlas_2025/data/validation_report.json) records original and derived hashes and the retained source anomalies.

The **6.277 million kWh/day** atlas total would be about **2.291 TWh/year** if repeated daily, far below the 2022 national consumer-electricity figure of 13.261 TWh. They have different service levels and coverage, so this is a scale warning rather than a calibration failure. The atlas's **17.59 million potential connections** are buildings, not customer records. Only **23** of 33,891 clusters have a wealth index value.

## Prioritized gaps for the electrification question

### Notebook D: system costs

**Section 10 is the current study:** four neighbouring Blue Nile clusters are optimized jointly, with a shared grid-side hub, binary service/route/repair choices and three recovery conditions. All 8,760 hours are retained. Demand, repairable infrastructure and regional supply conditions are declared scenarios. Numerical checks cover connected routes, equal delivered service, hourly feasibility, cost accounting and repair budgets. Geographic scaling and coupling to the national model are the next implementation steps. [Joint recovery method](RECOVERY_MODEL.md).

**Section 9 continues with available public proxies, without requiring measured settlement demand.** Eighteen clusters (one per state) receive location-specific 2022 hourly weather, atlas-derived daily energy and two explicit recovery-service targets. Source selection/building arithmetic, matched service, hourly operation and lifecycle costs are checked. Ten sites have conditional grid comparisons; eight outside the declared local-extension distance scope have off-grid comparisons only. No probability weights, nationwide budget or state-wide recommendation is inferred. The source atlas and weather have different vintages; this is not observed 2022 settlement demand. [Spatial proxy-demand method](../data/spatial_proxy_study/README.md).

**Section 8 adds exploratory uncertainty and break-even analysis.** Ten individual drivers and eight joint corners per cluster test conditional rankings. Operational cases are re-optimized for all 8,760 hours; geometry-only cost changes use exact fixed-cost adjustments under constant losses. Independent reconstruction checks hourly feasibility and complete lifecycle costs. Route thresholds and demand crossing brackets identify evidence priorities. Counts of scenario wins are not probabilities; capacities adapt separately, and no fixed-design, multi-weather-year or empirical validation is claimed. [Experiment assumptions](../data/electrification_uncertainty/README.md).

Sections 1–6 of the [cost notebook](../research/system_costs/Sudan_System_Costs.ipynb) account for 17 component types and 24 cost/finance parameters across four fixed 100-home designs. Nine tests cover hand-calculated cash flows, units, installed-cost scope and finance separation. Those fixed examples' cost per target kWh is not a feasibility-validated LCOE.

**Section 7 now adds a three-cluster hourly electrification pilot:** 18 optimal PyPSA cases, complete 2022 NASA POWER weather, identical assumed service targets, PV/storage/converter sizing and grid/diesel operation. Independent reconstruction checks 157,680 hourly case snapshots, energy and SOC balances, component/fuel/grid limits, lifecycle objective reconciliation and monotonic responses to removed supply options. Modelled LCOE uses hourly feasible delivery for this stylized system. Prices, routes, household counts and service profiles are **not independently field-validated**. Source SDG quotations remain separate from provisional USD prices; no actual exchange-rate conversion or current damage inventory is inferred. See [pilot assumptions and provenance](../data/electrification_pilot/README.md).

### October 2026 report review

The [new collection](../data/report_evidence/README.md) contains 23 evidence tables, plus source, issue and underlying-data-lead registers. It reviews 19 supplied PDFs (18 distinct documents), reusing the existing forecasting and DRE extractions. The [report-by-report review](../data/report_evidence/REVIEW.md) explains what was extracted and excluded.

Twenty-three arithmetic comparisons are recorded. Two source discrepancies remain: the rooftop-PV paper's formula inputs give 3,285 rather than 3,523 kWh/year, and the CSP paper's existing transmission lengths sum to 10,020.1 rather than 10,010.1 km. Other issues include a panel labelled 590 kW, contradictory grid assignment and unreconciled fleet scope. These checks improve traceability; they do not establish current conditions or independently validate published model results. No notebook capacities, costs or dispatch results were changed by this extraction.

| Priority | Needed input / decision | Why it matters | Minimum useful next deliverable |
|---|---|---|---|
| **1** | Verified access and households, productive/critical loads and hourly demand for mapped clusters | DRE provides geometry and a low-service building estimate but not true access or the required service | Pilot table joining DRE clusters to local evidence and multiple service scenarios |
| **1** | Usable/repairable grid, candidate routes, capacity and condition | Defines feasible connections, not merely nearest distance | Route table with endpoints, length, capacity and repair/extension assumptions |
| **1** | Validate the assembled lifecycle-cost inputs | Determines economic choice | Replace provisional prices with comparable installed-scope quotes, dated currency conversion, actual battery lives, repair/network costs and finance offers |
| **1** | Service and reliability requirements | Prevents an unfair comparison of a small solar-home system with continuous grid service | Quantity, peak capability, service hours and critical-load/shortage requirements |
| **2** | Renewable profiles/siting limits; seasonal hydro | Determines feasible generation and storage | Documented profiles; final candidates tested against fuller chronology |
| **2** | Recovery scenarios and implementation limits | Changes usable assets, timing and cost | Explicit low/central/high repair and demand assumptions, not an invented damage inventory |
| **2** | Boundary and asset crosswalks | Prevents double counting and wrong spatial assignment | Historical-to-study-area mapping; one record per physical asset/configuration/year |
| **3** | Independent validation and local review | Determines credible paper claims | Holdout comparisons, benchmark pilot cases, sensitivity maps and route/service review |

Missing exact damage records do not prevent scenario analysis. The claim becomes **conditional least-cost choices under documented recovery assumptions**, rather than a verified reconstruction plan.

## Claims today

**Supported:** a reproducible, nationally calibrated regional dispatch prototype; traceable historical datasets; mapped DRE clusters and reproducible source arithmetic; full lifecycle-cost accounting; local pilot and 18-state sample comparisons; and a four-cluster **joint recovery optimizer** with binary service/route/repair decisions, full-year operation and constrained regional supply. Section 10's hypothetical repair decisions are conditional on the declared candidate assets, not identified damaged infrastructure. See [scope and formulation](RECOVERY_MODEL.md).

**Not yet supported:** field-validated settlement recommendations, universal-access cost, joint national investment optimality, optimal repair priorities, a validated post-war grid map, distribution/security certification or treating 2012 projections as observations.

Use the [study plan](STUDY_PLAN.md) to move from these inputs to the intended planning results.
