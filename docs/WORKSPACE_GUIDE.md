# PyPSA-Sudan: what to open and what each result means

**Current scope decision:** follow the Zambia paper's two complementary branches, with three-hour national PyPSA steps and standard OnSSET settlement planning. Read [the agreed scope](ZAMBIA_ALIGNED_SCOPE.md) first. The existing settlement screen is a prototype with accounting and interpretation issues identified in review; its maps are not validated recovery recommendations.

## The current study in one sentence

Map settlement-level grid / mini-grid / standalone options with OnSSET, then test candidate grid repair and bulk-supply plans with PyPSA, under explicit post-conflict recovery conditions. The research question remains: **Where, and under what recovery conditions, are grid rehabilitation, mini-grids or standalone systems the least-cost way to provide reliable electricity in Sudan?**

## Read only these three first

1. **[Sudan → PyPSA-Earth handover notebook](../integration/pypsa_earth/Sudan_Earth_Handover.ipynb)** — active WSL integration, evidence roles, passing input checks and remaining baseline work. [Commands and locations](../integration/pypsa_earth/README.md).
2. **[Regional joint PyPSA notebook](../research/regional_joint_study/Sudan_Regional_Joint_Study.ipynb)** — completed full-year six-state national/grid-supply recovery cases; a prior planning formulation, retained as the supply-side reference and comparison.
3. **[Evidence and gaps](EVIDENCE_AND_GAPS.md)** — which inputs are observed, modeled, assumed or not yet known.

The [OnSSET study README](../research/onsset_pypsa_recovery/README.md) documents the earlier screen, which remains under correction. The [regional joint study README](../research/regional_joint_study/README.md) explains the 12 completed cases from the previous formulation. Open the HTML copies when you want figures immediately without running code. Neither is a completed result of the new Earth configuration.

## How the work fits together

| Layer | Current artifact | Scientific role | Current limit |
|---|---|---|---|
| Evidence | [DRE settlement atlas](../research/dre_atlas_2025/Sudan_DRE_Settlements.ipynb), [reports](../data/report_evidence/README.md), [cost ledger](../data/system_costs/README.md) | Sources for modeled settlement scale, distances, solar resource and planning costs | Access status, war damage and feeder topology are not observed |
| Settlement options prototype | [OnSSET–PyPSA recovery](../research/onsset_pypsa_recovery/README.md) | Earlier settlement screen | Accounting and recovery-attribution issues; under correction |
| National branch, active | [Earth handover](../integration/pypsa_earth/README.md) | Native Sudan inputs/configuration; three-hour standard workflow | Input checks pass; weather, fleet/import reconciliation and solve pending |
| National branch, earlier comparison | [Regional joint PyPSA study](../research/regional_joint_study/README.md) | Hourly dispatch, candidate corridor repairs and previously optimized 36-zone portfolios | 2022 reference system, schematic corridors and assumed outages |
| Earlier development | [System costs](../research/system_costs/Sudan_System_Costs.ipynb), [Gezira](../research/gezira_joint_planning/Sudan_Gezira_Joint_Planning.ipynb), [2022 dispatch](../Sudan_2022.ipynb), [historical forecasting](../research/forecasting_2012/Sudan_Forecasting_Replication.ipynb) | Transparent cost accounting, prototypes and cross-checks | These are **supporting / previous-stage studies**, not competing current recommendations |

**Do not sum** the new OnSSET LCOE-based annual service proxy and existing PyPSA annual system cost: they use overlapping service and energy costs. They can be compared and later coupled through a consistent demand and bulk-price interface.

## Next study sequence

The immediate implementation step is the [Earth baseline build](../integration/pypsa_earth/README.md#baseline-configuration-and-remaining-work): obtain weather/spatial inputs, reconcile plants and imports, then solve and validate. Evidence gaps below should be documented with explicit proxies where observations remain unavailable, rather than stopping the study indefinitely.

1. Validate a minimum set of **grid status and repair candidates**: substation and feeder location/voltage, pre-war connection status, usable capacity and observed damage/repair bill. The 2020–22 security layer is not a current damage map.
2. Define the target year and **service standard** (including evening availability) and calibrate DRE potential-building connections against observed population/access and consumption samples. Keep displacement and return scenarios explicit.
3. Replace the screen's simple PV/battery packages with hourly designs for a stratified set of grid, mini-grid and standalone settlements; use them to calibrate OnSSET cost curves and test reliability.
4. Follow the Zambia paper's complementary workflow: run national PyPSA recovery/expansion at three-hour resolution and standard OnSSET settlement access scenarios. Use consistent input definitions and explicitly reconcile their different demand and cost scopes. Iterative price feedback is outside the agreed main study.
5. Only then report robust settlement or administrative-area recommendations, uncertainty bands, investment sequencing and finance requirements. Document source licenses and reproducibility for publication.

This sequence uses OnSSET for geospatial electrification pathways and PyPSA for network, investment and dispatch interactions. The executable screen is an earlier prototype; the corrected Zambia-aligned runs remain implementation work.
