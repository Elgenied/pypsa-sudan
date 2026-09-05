# From starter model to a publishable PyPSA-Sudan study

**Study decision:** Use [2022 as the historical reference year](REFERENCE_YEAR_2022.md). The full-year national benchmark is solved; regional reconstruction and independent validation are outstanding. Current-year capacity and recovery scenarios are outside the selected baseline.

## The contribution to aim for

A new country name and an optimization that solves are not sufficient novelty. A strong contribution would combine a validated, reusable Sudan dataset with a question whose answer depends on Sudan's geography, conflict damage, fuel constraints, hydro dependence and dispersed electricity needs.

**Suggested question for the selected baseline:** How do hydro seasonality, fuel availability and transmission constraints affect Sudan's 2022 electricity dispatch, and how robust are the results to uncertain system data?

Possible contribution: an openly documented and validated 2022 regional network, with quantified uncertainty in hydro, demand, plant availability and network parameters. Establish novelty through a systematic literature search before choosing a final title or claiming this is the first Sudan model. The legacy starter's repair and recovery cases are demonstrations outside this historical baseline.

## Similar projects to learn from

| Example | What to learn | How Sudan should adapt it |
|---|---|---|
| [PyPSA-ZA, South Africa](https://github.com/PyPSA/pypsa-za) | A country-focused PyPSA model with spatial supply regions, documented inputs and an accompanying research paper | Retain regional modelling where utility data justify it; build Sudan-specific load, hydro and outage evidence rather than copying South African parameters |
| [PyPSA-Earth, demonstrated in Africa](https://arxiv.org/abs/2209.04663) | Reproducible open data-to-network workflow, spatial detail and operational/expansion studies | Use its upstream workflow to replace the starter's hand-curated corridor layer and generate country-specific weather data |
| [PyPSA meets Africa](https://arxiv.org/abs/2110.10628) | Motivation and methodology for an open African electricity-network model | Describe data gaps openly and contribute reusable corrections rather than presenting uncertain maps as precise engineering data |

This starter intentionally remains a small independent Python model. It is not a full execution or fork of PyPSA-Earth. Its `data/raw`, `data/curated`, `data/processed`, `config`, `src`, `tests`, `results` and `docs` folders provide a clear path to a larger workflow. A reference PyPSA-Earth configuration is supplied separately and has not been run.

## Publication gates

### 1. Reconstruct the selected 2022 historical case

Build a dated 2022 unit and network inventory. Reconcile net installed capacity, nameplate capacity, main activity producers and autoproducers. Ask local engineers to review the reconstruction. The legacy 2024 status ledger can provide names and source leads, but does not establish 2022 availability or connectivity.

**Deliverable:** dated asset-status ledger with uncertainty and named source documents, plus an explanation of what has changed between cases.

### 2. Replace the high-impact assumptions

| Priority | Data needed | Why it matters | Acceptance evidence |
|---|---|---|---|
| P0 | Monthly national/regional supplied energy; observed hourly demand or credible load profiles | Controls apparent capacity shortage and where power is needed | Match independent energy totals; distinguish served from latent demand |
| P0 | Unit-level operating capacity, outages, fuel availability and commissioning dates | Installed capacity can greatly exceed usable capacity | Reconcile plant sums and date-specific status with utility records |
| P0 | Substation connectivity, line voltage/circuits/length/rating, transformer limits and outages | Determines regional bottlenecks and viable repairs | Engineering review of topology and electrical limits; no unexplained automatic bridges |
| P0 | Monthly hydro generation, inflows and reservoir levels/releases | Hydro dominates the fleet and has seasonal water constraints | Calibrated energy balance and observed seasonal output |
| P1 | Import flows, firm capacity, contracts and border outages | Average imports are not firm dispatch ceilings | Reconcile hourly/monthly trade and interconnector capacity |
| P1 | Grid/rooftop PV, captive generation and isolated-system surveys | These may supply demand invisible to utility records | Explicit coverage estimate and uncertainty bounds |
| P1 | Fuel prices, heat rates, transport costs, O&M, rehabilitation/investment costs | Needed for economic comparisons | Consistent price year/currency and a transparent cost derivation |
| P2 | Population displacement, industrial/agricultural demand and critical-service locations | Spatial demand has changed; restoration benefits differ by region | Sensitivity to at least alternative spatial allocations |

The supplied `DATA_REQUEST_TEMPLATE.md` is ready to adapt for the utility, researchers or development partners. It has not been sent.

### 3. Increase temporal and physical credibility

Move to a full hourly year with correctly weighted snapshots and several weather/hydrological years. For a normal non-leap year this is 8,760 hours; 2024 is a leap year with 8,784. Test temporal aggregation against an hourly benchmark if using representative periods. A repeated synthetic week is not a substitute for seasonal validation.

Use PyPSA Lines and Transformers with defensible electrical parameters for questions requiring DC power flow; validate critical AC and voltage constraints separately when relevant. A regional transport model can remain publishable for an appropriately bounded planning question, but its transfer limits must be justified and conclusions must respect its limitations.

Hydro should use reservoir/inflow constraints, environmental and irrigation releases where material, and cascade relationships. Add solar and wind profiles from a reproducible weather workflow; include distributed generation and storage if comparing local supply to grid repair. Add ramps, minimum generation, maintenance and fuel-energy constraints when they materially change thermal dispatch. Include losses, reserves, contingencies or probabilistic outages when required by the research question.

**Deliverable:** documented formulation, input dictionary, transparent aggregation rules and convergence/sensitivity evidence.

### 4. Validate independently

Reserve observations that were not used for calibration. Compare monthly generation by fuel and major plant, imports, regional served energy, peak demand and credible outage/congestion patterns. Explain disagreements and bounds arising from incomplete coverage. Numerical feasibility alone is not validation.

Set project-specific error targets with a supervisor or domain partner before tuning the model; there is no universal percentage threshold that guarantees publication. Plot residuals and report absolute as well as relative error. Test uncertainty in hydro, demand magnitude and distribution, transfer capacities, import availability, fuel cost/availability, outage state and unrecorded solar. Report ranges and robust conclusions rather than a single optimistic case.

### 5. Make comparisons answer the question

Separate interventions: reconnecting two central corridors and doubling every transfer limit, as the starter's repair case does, cannot identify the benefit of an individual project. Create single-intervention and combined cases. Compare cost per unit of service restored, investment/operating cost, regional distribution of benefits, fuel dependence and emissions with defensible factors.

If modelling reliability probabilities, use stochastic outages/scenario probabilities and report EENS/LOLE correctly. Deterministic unserved energy from this starter is not an expected reliability metric. If selecting repair priorities, include engineering feasibility, cost and construction time. A lower shortage percentage alone does not establish cost-effectiveness.

### 6. Release a reproducible study

- Agree authorship and local collaboration; add real author names/ORCIDs to citation metadata.
- Tag a Git release, pin data versions and code revisions, and archive the permitted dataset and release on Zenodo for a DOI.
- Keep a separate data-rights manifest. Do not relicense third-party reports or derived OSM databases under the code license.
- Run the build and tests on a clean environment. Supply small CI tests plus scripts for the full study.
- Archive a full environment lock, solver settings, run hashes and reproducible figure scripts.
- Contribute vetted Sudan data corrections or adapters upstream; follow the receiving project's format and contribution requirements.

## Suggested manuscript structure

1. Introduction: Sudan's planning question, literature and precise contribution.
2. System and data: study dates, grid regions, assets, source hierarchy and uncertainty.
3. Methods: equations, spatial/temporal aggregation, hydro, outages and scenario design.
4. Validation: independent comparisons and unresolved gaps.
5. Results: benchmark and intervention cases, spatial effects and economics.
6. Robustness and limitations: data uncertainty, alternative assumptions and scope boundaries.
7. Conclusions: only findings supported across the tested assumptions.
8. Data/code availability: tagged repository, DOI, licenses and reproduction instructions.

Start with the validation/data gates, then choose a journal based on the final contribution. The deliverable is a functioning foundation, not a submission-ready paper.
