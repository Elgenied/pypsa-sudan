# Learning from the Zambia study: proposed redesign of PyPSA-Sudan

Review date: 20 October 2026. This document records the methodological comparison **before** the user chose an OnSSET-led settlement workflow. The [new OnSSET–PyPSA screen](../research/onsset_pypsa_recovery/README.md) is now implemented and is the active entry point; proposals below are retained as historical design analysis, not current instructions. The completed twelve-case Sudan regional PyPSA study remains the supply-side comparison.

## Source and reading boundary

Abuzayed, A., Chitandula, A., Nyoni, K. J., and Sola Vilalta, A. (2025), *Power system expansion and renewable integration for drought-resilient electrification in Zambia*, Energy Policy 206, 114786. DOI: https://doi.org/10.1016/j.enpol.2025.114786.

User-supplied source: `C:/Users/eelqu/OneDrive - University of Surrey/Desktop/pypsa_Zambia.pdf`, 20 pages. All pages were text-extracted and read; methodology, scenario, electrification-result and appendix figures were visually inspected. The mathematical supplement and separate validation report were referenced by the paper but were not available in this review. No claim of reproducing the Zambia results is made.

The public repository README was inspected: https://github.com/pypsa-meets-earth/pypsa-zm-data. It describes a country-data/configuration/validation layer used with PyPSA-Earth, rather than a standalone model. OnSSET's documentation was also inspected: https://onsset.readthedocs.io/en/latest/.

## What the paper actually does

- Sections 2.1-2.3, PDF pages 4-6: uses PyPSA-Earth for national generation/transmission/storage expansion, assuming all modeled loads are grid connected, and GEP/OnSSET for spatial electrification alternatives. Figure 3 shows parallel complementary branches. The main article does not document an iterative exchange of settlement choices, hourly demand and national marginal costs; do not describe it as a demonstrated joint optimum.
- Section 3, pages 6-7: compares network topology/line lengths, plants, demand, renewable potentials/capacity factors and hydro resources with external sources. Corrects country-specific plant records and hydro assumptions. The Kariba example illustrates the need to distinguish a shared facility's total capacity from the national entitlement.
- Section 4.1/Table 1, pages 7-8: twelve national scenarios combine three demand levels, two water conditions, and coal expansion allowed/prohibited. Normal hydro resource is set to 13 TWh; the low-water condition scales inflows to 67%. The demand levels are approximately 19.2, 28.8 and 38.4 TWh in the reported scenario figures.
- Section 4.2, page 8: electrification scenarios separately vary technology eligibility, solar costs and residential-only demand. These are not the same twelve national scenarios.
- Section 5/Figures 4-14, pages 9-16: reports installed capacity, generation, emissions, annualized costs, selected dispatch windows, technology/demand duration curves and electrification investments/coverage.
- Appendix Figure A.1, page 18: national transmission analysis uses 50 nodes derived from high-voltage infrastructure, with demand allocated to substation-related Voronoi areas. These are not equivalent to Sudan's 36 settlement-planning zones.

## Sudan comparison

The latest Sudan model is `research/regional_joint_study/model.py`, with its completed report `Sudan_Regional_Joint_Study.ipynb`. Its twelve cases completed on 19 October 2026. Earlier section-12 finite-library descriptions in the repository should not be confused with this joint grid-sizing extension.

| Dimension | Zambia article | Current Sudan regional implementation | Recommended action |
|---|---|---|---|
| Main question | 2030 expansion, drought resilience and universal access | Conditional least-cost recovery and service in six states | Retain the Sudan recovery question and geography |
| National supply | Generation, storage and transmission expansion | Fixed national fleet, dispatch and four repair candidates | Add bounded new utility PV/storage and eligible rehabilitation |
| Spatial allocation | Infrastructure-related national nodes plus separate settlement electrification | Six geographic planning zones per state; whole-zone service choice | Use verified/provisional supply catchments, with within-catchment settlement diversity |
| Supply/access coupling | Complementary branches; iterative closure not documented | Grid-connected local equipment/operation, national dispatch and repairs jointly selected | Preserve direct coupling or explicitly verify a decomposed feedback process |
| Demand | Synthetic projections and access scenarios | Historical residential allocation plus a service floor and synthetic profile | Distinguish restoration, access expansion and productive/critical loads |
| Disruption | Hydro-resource stress | Corridor capacity restrictions plus local interruption schedules | Separate water, plant availability, transmission damage and distribution interruptions |
| Validation | External-source comparisons and country corrections | Detailed numerical replay/checks; weaker independent engineering validation | Add an explicit empirical validation notebook |
| Outputs | National investment, generation, emissions, access and dispatch | Regional choices, local equipment, repairs, dispatch, costs and checks | Add incremental recovery costs and bottleneck diagnostics |

## Proposed architecture

1. **Evidence and reference system.** Preserve the 2022 baseline, original observations, source dates and uncertainty flags. Create reconciled plant, substation, line, settlement and cost registers. Nameplate capacity, usable plant capacity, fuel availability and hydro energy are separate fields.
2. **National supply and recovery layer.** Retain PyPSA dispatch and repairs. Add new utility-scale PV and storage at a small set of defensible candidate buses, with land/resource and capacity bounds. Distinguish expansion from restoring existing assets. Wind is a later addition when site and profile evidence support it.
3. **Spatial service layer.** Retain every source settlement ID. Assign plausible supply substations and routes. Permit different service choices for dense/near-grid, dispersed and remote settlements within a catchment. Treat topology-derived catchments as planning constructs, not verified feeder territories.
4. **Coupling and hourly verification.** Settlement grid choices must produce chronological imports at the correct upstream buses. Costs must use national operation consistently. Selected local equipment must serve load through local interruptions and national scarcity. If decomposing the problem, iterate and document convergence, cost accounting and fixed-investment feasibility; do not claim a global optimum from convergence alone.

Conceptually:

`evidence -> national supply/repair choices <-> spatial service choices -> fixed-investment hourly checks -> costs/maps/policy findings`

Keep heavy optimization in resumable scripts and use notebooks to explain inputs, run status and saved results. Software migration is secondary to the quality of these interfaces and evidence.

## Priority 1: a supply-side comparison

The current fleet cannot add utility-scale generation. It can change dispatch, repair corridors and add local equipment. This can favor local PV/storage relative to a future system allowed to build new upstream PV/storage. The direction and size of the geographic effect require new solves; they cannot be inferred as an established result.

First extend one selective mixed case with costed, bounded national PV and storage candidates while preserving its demand, weather, repair rules and local alternatives. Reconcile the national and local technology-cost boundaries, and verify that allowing new candidates cannot worsen the true optimum under otherwise identical assumptions. Compare solver bounds before interpreting tiny differences.

Report changes in local technology choice, local versus utility capacity, repairs, hourly bottlenecks and cost. Do not merely add a cheap unlimited bulk generator: it would bypass the network and resource constraints under study.

## Priority 2: supply-catchment and settlement diversity

Six zones per state are reproducible computational groups, but not electrical service territories. The latest 48-zone comparison changed inherited service modes for roughly 10% of potential connections while aggregate cost moved by less than 1%. This motivates geographic improvement more directly than increasing the number of national scenarios.

Develop a cluster-to-substation/candidate-route crosswalk with confidence flags. Subdivide by electrical connectivity, route cost, density and remoteness where justified. Avoid replacing one arbitrary fixed zone count with another. Do not infer a usable connection from distance to a transmission line, and do not automatically adopt the Zambia article's 50 km MV-extension limit for Sudan.

Do not begin with 11,268 separate full-year mixed-integer sizing problems. Cache normalized off-grid designs or justified archetypes, screen dominated alternatives and aggregate hourly grid imports at upstream buses. Preserve cluster-level memberships and validate the approximation against finer subproblems. A soft-linked OnSSET comparison is useful as an independent spatial benchmark; replacing the current hourly core is not required.

## Priority 3: independent validation

Create a concise reference-system validation notebook covering:

- Plant identity, ownership/country share, fuel, location, nameplate and available capacity.
- Substation/line identity, voltage, connectivity, route length and uncertainty.
- Annual generation by carrier, consumption and losses, with accounting boundaries reconciled.
- Monthly hydro generation/energy limits, distinguishing water scarcity from mechanical unavailability.
- Solar capacity factors and seasonal patterns against another appropriate resource product or published observations.
- Settlement coverage, connection definitions, source demand formulas and inferred access labels.

Show external observation, model value, difference, source/date and any correction. Numerical balance checks are necessary but cannot replace these comparisons. Matching an annual calibration target is not independent validation. Differences between technical renewable-potential studies require harmonized definitions before a comparison is meaningful.

## Demand and cost reporting

Keep the existing equal-service comparisons. Introduce explicit demand components when evidence permits: restoration of reference residential service; additional basic access; and productive/critical service. Unknown access status should remain unknown or be represented by bounded scenarios. Nightlight absence and historic risk labels do not establish current access or safety. Do not translate buildings into people without a documented demographic mapping.

For costs, keep separate: (a) total system annual resource cost, (b) initial new/rehabilitation spending, and (c) incremental program cost relative to a matched background-system counterfactual. Use the same recovery restrictions in that counterfactual. Shared repairs may benefit both existing loads and the access program; state the attribution rule. Do not subtract all upstream costs and assume their service is free.

The Zambia article uses a 7% discount rate; Sudan currently uses 10%. The former is not a Sudan financing estimate. Its per-capita electrification investment ratios are not directly comparable with Sudan's annual system costs or per-building quantities. In particular, distinguish total served population from newly served population before calculating cost per newly connected person.

## A compact future experiment set

Do not rerun a large grid of assumptions immediately. Start with the single expanded-supply selective mixed diagnostic. After formulation and evidence checks, a proposed main study could use three recovery conditions times two supply-investment permissions (repair/operate existing fleet; repair plus bounded new utility supply): six mixed cases. Add grid-led and decentralized benchmarks under the selective expandable-supply condition, and two focused checks for demand and hydro stress: ten main runs in total. Geographic approximation checks remain a separate validation task.

This is a proposal, not a claim that the old and new cases can be compared without harmonizing inputs. Recovery packages can retain their policy interpretation, but a matched counterfactual must hold other availability assumptions constant when attributing savings specifically to a repair.

## Outputs to learn from and improve

- Capacity additions split into restored existing assets, new utility supply and new local systems.
- Electricity production/imports, with batteries treated as storage rather than a primary energy source.
- Annualized capital/replacement, fixed and variable operating costs, and initial spending.
- Maps of preferred service, uncertainty, repair corridors and binding bottlenecks.
- Critical-hour plots selected by rules: peak demand, tightest corridor, lowest battery state and low hydro/solar periods; retain full-year checks.
- Duration curves for flows, net load and battery operation; explain that sorting removes chronology.
- Cost and mode-switch differences between restricted, selective and restored recovery.
- Operational emissions if fuel-specific generation/efficiency/emission factors are documented; distinguish them from lifecycle emissions.

Hourly adequacy, steady-state flow feasibility and dynamic frequency/voltage stability are different claims. Neither selected dispatch windows nor zero annual unserved energy alone establish dynamic stability or probabilistic resilience.

## What to preserve

Preserve the present completed twelve-case study, original evidence, cost ledger, caching, manifests, source-ID coverage and independent replay/checks. Treat it as the fixed-fleet recovery baseline. Make an extension in a separate research module and notebook. The main scientific objective remains the Sudan-specific value of repair versus independent supply, strengthened by spatial evidence and a fair upstream investment choice.
