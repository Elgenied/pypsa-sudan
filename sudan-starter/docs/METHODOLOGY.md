# Model definition and limitations

> **Reference update:** The default is now the [2022 national benchmark](REFERENCE_YEAR_2022.md). Descriptions of the 19-region model, 2024 fleet status and six scenarios below refer to the separate legacy illustration.

## Scope

The study boundary is Sudan, separate from South Sudan. The model is a lossless regional economic-dispatch linear program. It covers a **synthetic 168-hour week beginning 1 August 2024**, anchored to a documented fleet-status snapshot of that month. Dates identify the modelling horizon; they do not turn synthetic profiles into observations.

There are 19 regional buses, 20 domestic plant records, two import supplies and a shortage variable at every bus. The seven isolated systems are retained as separate components. These are regional abstractions, not a complete substation model or national electrification model.

## Mathematical formulation

Minimize the sum across plants and hours of dispatch (MW) × snapshot duration (hours) × marginal cost (USD/MWh), including imported supply and a USD 10,000/MWh shortage penalty.

For every bus and hour:

`physical generation + imports + unserved demand + incoming transfers - outgoing transfers = requested demand`.

Constraints:

1. Plant dispatch lies between zero and installed MW × available fraction.
2. Each lossless corridor has `-transfer_mw <= flow <= transfer_mw`.
3. Each hydro plant has a horizon energy budget: `sum(dispatch × hours) <= available_MW × horizon_hours × 0.65 × scenario_hydro_multiplier`.
4. Unserved demand lies between zero and that bus's requested hourly load. It is a slack variable, not a real resource.
5. All capacities are fixed. There are no investment variables.

One snapshot represents one hour; objective and generator energy weights are both one. Summing MW values produces MWh only because of these explicit weights. There is no annual extrapolation. When the horizon changes, the synthetic profile is renormalized and the hydro budget scales with the number of hours.

## What is observed, interpreted or assumed

**Reported facts:** plant capacities and dated status originate in World Bank Annexes 1–2. Historical WRI coordinates are used only for manually identified matches. Original reports and GIS are preserved with download hashes.

**Interpretations:** a plant described as available is allowed full instantaneous output, subject to hydro energy budgets. Unquantified partial diesel availability is set to 50% of nameplate. Reported import levels (60 MW Egypt, 50 MW Ethiopia) are used as ceilings; these are not verified NTCs or guaranteed contracts. Liquid-fuel turbines are classified as oil rather than automatically as natural gas.

**Assumptions:** every regional load, hourly demand shape, domestic transfer limit, marginal cost and hydro budget. Costs are illustrative USD/MWh with no calibrated price year, fuel conversion, efficiency estimate, subsidy or exchange-rate treatment. The hydro coefficient is an energy allowance, not an observed plant capacity factor or river inflow.

The northern/southern split follows the report's prose. Exact damaged branches are unknown; two central connections are disabled to implement a regional split. Residual Khartoum-region demand represents an illustrative aggregate including Omdurman, not a claim that disconnected Khartoum city was fully supplied. Wad Medani also retains an assumed residual demand. These choices require regional observations before empirical interpretation.

## Transmission treatment

The downloaded AICD shapefile has 30 source features, including historical existing, planned, missing and under-study projects. The model does not promote all of them to operating lines. The extraction assigns stable source IDs, preserves attributes, clips a display layer to a coarse modern boundary, and records review actions.

The 13 model corridors are hand-curated regional aggregations informed by the report map and historical endpoints. Their numerical capacities are assumptions. A map line's voltage alone is insufficient to determine its thermal rating, stability limit, or available transfer capability. No line resistance, reactance, transformers, circuit count or voltage-control limits are invented. Consequently, this model enforces energy balance and transport limits but **does not enforce Kirchhoff voltage law, AC feasibility, losses or N-1 security**.

## Hydro, shortages and interpretation

Hydro budgets prevent unlimited free hydro generation. They do not represent reservoir storage, irrigation releases, environmental flow, cascades, inflow seasonality or cross-border water allocation. Perfect foresight allows the weekly energy to move between any hours. Use calibrated inflows and reservoir constraints before studying seasonal resilience.

All buses share a shortage penalty. Several equally optimal spatial and hourly shortage allocations may therefore exist. Regional outputs are one feasible optimum, not a fairness rule or a unique load-shedding schedule. The national energy shortage is **modelled unserved energy**, not probabilistic expected energy not served (EENS). Hours with shortages are not a probabilistic loss-of-load expectation (LOLE).

Solar home systems, rooftop PV, captive industrial generation, batteries and some small plants are not inventoried. Their exclusion does not establish zero real-world capacity. The included fleet totals 3,647.4 MW; this is the sum of the selected report records, not an independently validated current national total.

## Conflicts retained for review

- Setit/Upper Atbara is assigned south from the report's prose; the annex labels it north. Verify connectivity with the utility.
- WRI has two Jebel Aulia 15.2 MW records; the curated inventory has one 30.4 MW station. Historical rows are not appended blindly.
- WRI country labels include Kuku and Melut Sugar Factory, located in present-day South Sudan. They are excluded. The coarse boundary also flags the coastal Port Sudan entry; this is a shoreline-resolution issue, **not evidence the plant belongs to another country**. It is retained for review and not matched to the Turkish barge.
- Several WRI capacities differ from the newer report; the report is the chosen inventory basis. WRI only supplies historical coordinates for matched records. Nine records have regional location proxies.
- Kosti is 500 MW in the selected report. Do not silently replace it with differently reported gross/unit totals without a reconciliation.
- Garri 4 fuel classification and newer Garri/Port Sudan commissioning need confirmation. Planned assets are not assumed commissioned.

## Verification

Each solve must return optimal. The exporter then checks nodal balance, nonnegative generation, instantaneous generator bounds, corridor bounds, hydro energy and hourly local shortage bounds. It reconstructs the optimization objective from dispatch and costs. Regression tests check shut-down plants, finite hydro, component separation, repaired connectivity, demand normalization and NetCDF round trips. Scenario-direction checks compare restricted feasible sets and repaired networks.

These checks verify implementation and numerical accounting. **They do not empirically validate the synthetic inputs.** A publishable result needs independent observations, an explicit validation period and sensitivity/convergence checks.
