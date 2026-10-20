# Agreed Sudan study scope: follow the Zambia approach

Updated 20 October 2026 after the user's request to avoid unnecessary hourly and coupling complexity.

## Methodological reference

Abuzayed et al. (2025), *Power system expansion and renewable integration for drought-resilient electrification in Zambia*, Energy Policy 206, 114786, https://doi.org/10.1016/j.enpol.2025.114786.

Section 2.3 and Figure 3 describe two complementary branches: PyPSA-Earth national generation/transmission planning assuming grid-connected loads, and GEP/OnSSET spatial electrification alternatives. The article does not establish an iterative joint OnSSET–PyPSA optimum. Section 3 describes hourly GEGIS demand inputs. The public `pypsa-zm-data/configs/config.zm-default.yaml` uses `opts: [Co2L-3H]`, indicating three-hour temporal aggregation, and ten spatial clusters. The article's appendix shows 50 national nodes. Therefore the public default is evidence that three-hour aggregation is used in the project, **not proof of the exact configuration used for all published results**.

Configuration inspected: https://github.com/pypsa-meets-earth/pypsa-zm-data/blob/main/configs/config.zm-default.yaml.

## Decisions for Sudan

| Item | Adopted scope |
|---|---|
| Reference system | Retain the documented 2022 Sudan reference, with dated evidence and explicit proxy inputs |
| Geography | Six-state access focus: Northern, River Nile, Khartoum, Gezira, White Nile, Sennar; retain external national supply and transfers |
| National branch | PyPSA generation, storage, transmission-capacity/repair and dispatch planning |
| National time steps | Three-hour chronological averages for one complete weather year: 2,920 steps for 2022, with three-hour objective, energy and storage weights |
| Access branch | OnSSET settlement electrification with standard cost, demand, resource, grid-extension and eligibility inputs |
| Local reliability | Use defensible technology assumptions and existing representative hourly designs as supporting evidence; no new hourly optimization for all 11,268 settlements |
| Relationship between branches | Complementary analyses with consistent source definitions and explicitly stated cost/demand boundaries; no iterative coupling required for the main study |
| Sudan contribution | Post-conflict recovery scenarios: limited rehabilitation, targeted rehabilitation, broad restoration |
| Main experiment size | Three recovery scenarios in each branch; one matched no-repair comparison to isolate rehabilitation benefits where required |
| Outputs | National capacity/generation/cost/repair results; settlement technology maps and access investment; clearly separate system costs from electrification spending |
| Validation | Correct cost accounting, reconcile inputs, check physical balances and storage duration; one selected national design can be checked at hourly resolution if aggregation affects the conclusions |

Three-hour aggregation must average power profiles and retain duration weights. Simply selecting every third hour is not acceptable. Short distribution outages should not be converted to an arbitrary uniform electricity-price surcharge and then interpreted as the benefit of specific transmission repairs.

## Implementation sequence

1. Correct the existing screen's maintenance, losses, replacement reporting and unsupported reliability labels. Keep its 1,304 ranking switches as a superseded prototype result.
2. Prepare a small, reproducible Sudan configuration and validation register following the Zambia country-data structure. Distinguish the common residential service target from additional national industrial/commercial demand.
3. Run the national three-hour recovery/expansion scenarios, holding demand and other assumptions fixed for comparisons that attribute benefits to repairs.
4. Run the standard OnSSET access scenarios, with documented baseline access calibration or explicit provisional alternatives when observations are absent.
5. Present the complementary results in one main notebook. Explain when a recommendation is conditional on assumed infrastructure status.

This scope replaces the proposed custom settlement-selection master model and mandatory iterative price-feedback work. It is a recorded implementation decision, not a claim that the corrected runs already exist.
