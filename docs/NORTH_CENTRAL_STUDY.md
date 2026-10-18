# Proposed regional study: electricity recovery in northern and central Sudan

Status: **scope prepared; regional optimization not yet implemented or run**. Section 11 remains the latest completed optimization. This document defines the next research study, rather than presenting new technology recommendations.

## Research question and boundary

**Where, and under what grid-recovery conditions, should northern and central Sudan rehabilitate grid supply, develop mini-grids or use standalone systems to restore and expand reliable electricity service at least lifecycle cost?**

Use **Northern, River Nile, Khartoum and Gezira** as the proposed administrative core. This covers the northern-to-central study corridor without pretending that administrative boundaries identify electrical islands. Retain the rest of Sudan's supply system as an external coupled network: generation outside the study area and interregional transfers still affect regional choices. White Nile and Sennar are an explicit optional geographic extension; their supply assets remain relevant even if their settlements are outside the core.

The frozen atlas contains **8,077 clusters** in the four-state core: Northern 1,345; River Nile 2,072; Khartoum 1,818; Gezira 2,842. Including White Nile and Sennar would give 11,268. The core's 7,956,151 potential building connections are neither verified households nor an estimate of unconnected customers. Do not report this as the number needing electrification.

The study must include existing urban/peri-urban demand and rural access opportunities. Do not reuse the eight-cluster selection rule that excluded nightlight sites and clusters larger than 500 potential connections. Every core source cluster should appear in a coverage table, including explicit aggregation and exclusions.

## What the evidence supports

The [World Bank's September 2024 sector update](https://documents1.worldbank.org/curated/en/099080625100525928/pdf/P171810-aceaafc9-7439-4838-974c-81284effd33a.pdf), published in 2025, reports north/south grid separation and bottlenecks associated with damage and displaced demand (PDF pp. 6–7). These are dated observations, not verified present-day operating conditions. Use them to motivate limited-connectivity and restored-connectivity cases. The report's conflicting Upper Atbara island assignment is already recorded in `data/report_evidence/source_issues.csv`; do not turn that unresolved label into an assumed bus disconnection.

The [public transmission shapefile](https://energydata.info/dataset/sudan-electricity-transmission-network) has a historical 2009 release vintage. The settlement atlas gives proximity to mixed/unknown-voltage lines. Neither proves usable tie-ins or present ratings. Historical routes, report maps and open line/substation geography must be reconciled in an asset register, with uncertain topology and capacity visibly marked.

## Minimum model changes

1. **Geographic coverage and supply zones.** Register all core atlas IDs; connect spatially contiguous planning zones to documented or explicitly assumed grid interfaces. Preserve a cluster-to-zone crosswalk. Start with roughly 30–60 planning zones as a computational design target, then test whether the decisions change with finer aggregation. Do not turn a zone-level result into an asserted per-building recommendation.
2. **Demand accounting.** Separate restoration of existing service from additional access. Allocate the 2022 aggregate baseline consistently across regional loads; do not add the whole atlas demand on top. Building-based hourly profiles remain documented service scenarios. Distinguish household service from commercial, industrial, irrigation and critical loads where the reports support their allocation. Nightlight absence is not proof of disconnection.
3. **Recovery of shared infrastructure.** Replace the single hypothetical local feeder with candidate repairable corridors, substations and local extensions. Document each asset's evidence, availability assumption, capacity, repair cost and resulting connectivity. Physical damage and fuel unavailability are separate constraints. Retain outside-region generation and transfers; add import or generation investment options only with consistent cost and capability assumptions.
4. **Fair local alternatives.** Offer local grid plus backup, shared mini-grids and standalone systems, including connection/distribution costs and replacement/O&M. Existing connected areas can choose local support without treating their historical assets as new greenfield construction. Shared mini-grid grouping must be explicit; today's model only optimizes independent off-grid clusters and one grid-side hub.
5. **Chronology and reliability.** Retain chronological storage and annual/seasonal hydro constraints. A reduced planning time resolution may be used only with documented approximation checks and an 8,760-hour feasibility replay with installed capacities and choices fixed. Record unserved energy and outage hours; do not infer field reliability from a feasible synthetic year.
6. **Regional computation.** Use spatial aggregation and coordinated subproblems rather than multiplying the existing 8,760-hour mixed-integer model across 8,077 sites. PyPSA supports [network clustering](https://docs.pypsa.org/stable/user-guide/clustering/); the chosen aggregation must preserve relevant bottlenecks. Carry upper/lower bounds where applicable and label heuristic allocations if there is no global certificate.

## A small, fixed experiment set

Use the same service target, price basis and economic horizon for three recovery conditions: restricted backbone; selected backbone repairs; restored connectivity with remaining capacity limits. Define the changed assets explicitly before solving. Compare an optimized mixed-technology plan with a feasible grid-led restoration benchmark and a decentralized-first benchmark, all at the same service target. Apply a common transparent capital constraint only if studying a budget-constrained policy question; report infeasibility or service shortfall instead of silently reducing demand.

The first regional paper can use a **single defined recovery-stage design** with lifecycle costs. Do not claim optimal reconstruction timing unless a later model explicitly represents investment periods, repair lead times and asset carry-over. A compact demand/fuel-cost check and a spatial-resolution check are sufficient initial robustness work; a large new assumption sweep is not the immediate priority.

## Deliverables and completion criteria

- One clearly titled regional results section in the existing notebook, with a coverage map and accounting table before any technology map.
- Preferred service arrangements and uncertainty/aggregation labels; potential service points and delivered energy, with no conversion to households without evidence.
- Selected repairs/extensions, local and upstream capacities, initial spending, annualized/lifecycle costs and fuel dependence.
- Hourly adequacy with fixed investments, seasonal hydro treatment, network capacity/balance checks and objective reconstruction.
- Comparisons against the two policy benchmarks, numerical solution quality and a spatial-resolution check.
- Source/version manifest, executable workflow and claims matched to dated evidence. This is a reproducible scenario study, not a field-certified reconstruction plan.

**Immediate implementation:** prepare the regional asset/interface register and demand-to-zone allocation, then solve a reduced regional integration case to check runtime and accounting before expanding to every planning zone. Merely running more independent small villages would not answer the regional recovery question.

## Scope files

Run `python research/system_costs/prepare_regional_scope.py` to regenerate [coverage](../data/north_central_study/coverage.csv), [source-ID membership](../data/north_central_study/scope_membership.csv) and [provenance/status](../data/north_central_study/scope_manifest.json). These are an inventory, not modelled electrification results. The membership table points back to the existing atlas rather than copying its full attributes.
