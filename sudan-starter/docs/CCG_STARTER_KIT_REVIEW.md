# Assessment of the CCG Sudan starter dataset

Reviewed 5 September 2026. Source: Cannone and colleagues, [Selected 'Starter Kit' energy system modelling data for Sudan, version 2](https://www.researchsquare.com/article/rs-479952/v2), DOI [10.21203/rs.3.rs-479952/v2](https://doi.org/10.21203/rs.3.rs-479952/v2).

**Useful for a historical planning reference and better parameter provenance; insufficient to reconstruct current grid operation.** The model's solved baseline has not been changed by this review. Reference inputs are kept separate until their meaning, dates and units are reconciled.

## What has been downloaded

The paper points to Zenodo DOI `10.5281/zenodo.4725460`. Resolving its API returned **record 4756665, version v1.2.0, dated 13 May 2021**. The exact resolved record is [10.5281/zenodo.4756665](https://doi.org/10.5281/zenodo.4756665). This distinction is preserved rather than calling the retrieved files v1.1.0.

`data/reference/ccg_sudan_2021/` contains nine numbered CSV tables, a residual-capacity CSV, the original README, bibliography, complete record metadata and a download manifest. Each downloaded file was verified against Zenodo's MD5 checksum; a local SHA-256 is also recorded. The approximately 43 MB SAND macro-enabled workbook was not downloaded or executed. Consequently, workbook-only demand profiles and detailed asset records have not been inspected.

The repository metadata and original README identify the deposited data as **CC0**. The Research Square article itself identifies **CC BY 4.0**. These are different licenses for different objects. Attribute the authors and original sources in either case.

## How the tables can help

| Source item | Useful application | Required care |
|---|---|---|
| Table 1 and residual-capacity file | Cross-check technology totals for a pre-conflict reference | Historical estimates and retirement assumptions do not establish current available MW |
| Tables 2–3 | Efficiency, lifetime and capital/fixed-cost starting points | Check price year, regional applicability and technology/fuel matching; future values are projections |
| Table 4 | Aggregate transmission/distribution cost and loss assumptions | Does not provide branch topology, reactance, circuit count or individual MW/MVA ratings |
| Table 6 | Transparent reference fuel-price assumptions | Reconcile delivered fuel, transport, currency and study date before dispatch use |
| Table 7 | Consistent fuel-specific CO2 accounting | Distinguish combustion factors from lifecycle emissions and apply efficiency correctly |
| Tables 8–9 | Broad resource constraints and contextual checks | Resource potential is not installed or immediately buildable capacity |
| Article demand estimate and underlying TEMBA reference | Historical annual energy benchmark | Separate final consumption from generation, projections from observations, and annual totals from hourly profiles |

For example, the article gives estimated **2018 final electricity demand of 45.53 PJ**, equivalent to **12.65 TWh** (`PJ / 3.6 = TWh`). This is a useful historical benchmark, not a 2024/2026 demand observation. The actual demand series is not among the small CSV files downloaded here.

The table's **0.43 hydro capacity factor** is an aggregate reference. It should not directly overwrite the model's assumed **0.65 weekly hydro-energy allowance**: the aggregation and time basis differ. The article states that its solar capacity-factor averaging uses daylight hours; a **0.26** value must not be treated automatically as an all-hours annual factor.

## Translation into PyPSA

Before implementing a cost-calibrated scenario:

- Convert fuel cost from USD/GJ to USD/MWh of electricity as `fuel_cost * 3.6 / efficiency`, then add separately justified variable O&M.
- Convert capital cost from USD/kW to USD/MW by multiplying by 1,000. For capacity expansion, annualize with a stated discount rate and lifetime, then add annual fixed O&M in consistent units.
- Keep annual fixed O&M separate from dispatch marginal cost. Do not move it into USD/MWh without a defensible methodology, especially where source assumptions combine cost categories.
- Convert fuel CO2 factors from kg/GJ to tonnes/MWh of fuel as `factor * 3.6 / 1000`; divide by efficiency for a per-MWh-electricity reporting factor.
- Represent time-varying renewables with hourly profiles. A technology-average capacity factor is neither a plant outage record nor a complete renewable profile.
- Check liquid-fuel versus natural-gas turbines by plant. A technology label containing 'gas turbine' does not establish its fuel supply.

These are suggested integration rules; no new costs, capacities or dispatch results have been applied automatically.

## Remaining research gaps

The highest priorities remain dated plant availability, regional observed demand, verified substation/line connectivity and ratings, hydro inflows/operation, imports, fuel supply and distributed solar. Obtain an independent set of observed monthly generation and consumption for validation.

The paper describes deriving capacity estimates through PLEXOS-World using WRI-based information. Agreement with the WRI inventory is therefore not automatically independent validation. Reconcile major plant capacities and Sudan/South Sudan geography against independent utility/manufacturer evidence.

Recommended next experiment: build a **separate historical reference case** with a stated year and these source-based parameters, validate it, and only then apply dated conflict/recovery changes. Preserve the existing illustrative baseline as a reproducible example.
