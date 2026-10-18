# Joint recovery planning demonstration

**Question:** Where, and under what recovery conditions, are grid rehabilitation, mini-grids or standalone systems the least-cost way to provide reliable electricity in Sudan?

Start with **section 10** in [the existing study notebook](../research/system_costs/Sudan_System_Costs.ipynb). This is a four-cluster Blue Nile joint planning model, not the completed national electrification model. No additional measured demand is required to reproduce it.

## Scope and evidence

The source DRE atlas supplies coordinates, potential connections, cluster area and line proximity. The existing Al Kurumuk pilot anchor and its three nearest eligible Blue Nile neighbours are selected before optimization. Eligibility: 20–500 potential connections, positive area, no detected source nightlight. The four clusters total 880 potential connections. Source names are retained alongside stable geohashes; one placeholder name is not invented. The anchor's NASA POWER 2022 hourly weather is reused explicitly across this 2.21 km neighbourhood.

Demand is a common **1 kWh per potential connection/day** scenario. There is also an assumed separate 30 kW-peak existing-load block, not total Blue Nile consumption. Candidate settlement load is excluded from that block by definition. The 2022 national model is contextual, not dynamically coupled.

The root feeder is a hypothetical repairable 2.002 km connection: source anchor proximity times 1.3. Repair at 35% of the new-line component rate and one upstream restoration allowance come from declared scenario inputs and the existing ledger. No current damage, voltage, tie-in location or physical capacity is inferred from atlas proximity or historical conflict categories. The upstream aggregate supply block is not an identified generation plant.

## Formulation

Each settlement has one binary primary-service choice: grid, mini-grid or standalone. The independent off-grid options are first optimized over 8,760 hours, then supplied to the joint mixed-integer model as fixed-service, minimized-cost columns. This is exact for the options offered, because their operating decisions have no coupling to other settlements or shared resource constraint. If regional fuel budgets, shared mini-grids or differing demand profiles are introduced, this decomposition must be revisited.

The PyPSA model jointly optimizes grid-connected PV, battery energy, converter power, diesel, full-year operation, six possible intersettlement route activations, and common-feeder/upstream repair decisions. **The grid option offers one shared generation/storage hub at S1**, with capacity bounds scaled to all 880 connections. Other grid-connected settlements receive supply through the chosen edges; grid-side generation/storage at those sites is not offered. Repairing the common feeder requires S1 to select grid service. This explicit restriction makes the result an optimum within the declared single-hub candidate architecture, not unrestricted regional planning. Binary service choices gate generation/storage and delivered load. A separate commodity-flow connectivity constraint requires every selected grid site to have a selected path to the repaired common feeder. Non-root transit nodes can remain locally off-grid.

Each undirected candidate route has two lossy directional links and a shared capacity/activation constraint; its fixed cost is charged once. Routes use great-circle length times 1.3, 400 kW capacity and 98% directional efficiency. These are screening assumptions, not AC or engineering designs. Grid local distribution loses 10%, mini-grid distribution 8%, and standalone has no shared distribution. Transformer quantities scale to the selected site's peak using an assumed 80 kW usable rating per 100 kVA unit. Converter input/output ratings, cycling and efficiencies follow the existing pilot.

Valid rooted cutset constraints strengthen the connectivity relaxation. The higher-cost independent off-grid option at each settlement is eliminated by dominance: it supplies exactly the same service and has no shared constraints, so this cannot improve the optimal objective. The retained least-cost off-grid option is still compared with joint grid investment. A numerical charging penalty of 0.001 USD/MWh discourages degenerate cycling and is subtracted from reported resource costs.

No load-shedding variable exists. All modelled hours must balance. Grid-connected settlement diesel is limited to 20% of aggregate grid-connected delivered annual energy, and each independent mini-grid has the same fractional limit. Standalone has no diesel. A 30 kW backup with costed tank supports the separate existing-load block; backup dispatch cannot exceed that block's hourly load, and common-feeder flow cannot exceed aggregate bulk supply. This does not establish probabilistic reliability under unmodelled outages.

## Recovery conditions

| Case | Repair budget USD | Existing upstream capacity | Synthetic unavailable local hours |
|---|---:|---:|---|
| Constrained | 0 | 40 kW | 18–23 |
| Partial | 30,000 | 60 kW | 19–21 |
| Broad | 100,000 | 80 kW | None |

An optional upstream repair restores another 150 kW, subject to the same availability profile. These are alternative stationary conditions, not a historical damage assessment or sequenced transition. All other demand/cost inputs stay fixed. Only initial repair costs are constrained by the stated repair budget; new investments remain in the objective but are not under that budget. Exogenous improvement outside the regional boundary is not charged as a modelled national repair, so cost differences are not national recovery benefit-cost estimates.

The objective minimizes equivalent annual lifecycle cost. The existing detailed ledger supplies replacements, logistics, installation, maintenance, retirement and project allowances. All costs are constant-2025 USD over 20 years at a real 10% discount rate. Nonrecoverable tax is set to zero in this new module to keep the resource-cost comparison free of that transfer; previous sections retain their own documented cost basis. Bulk supply retains its 0.15 USD/kWh service-resource allowance at the regional boundary. Incremental repair is additional, with no charge for sunk original construction. Shared assets are charged once, not separately to each downstream settlement. No retail tariffs, debt repayment or grants enter this objective.

## Files and reproduction

- Inputs: [data/recovery_planning](../data/recovery_planning) — config, four source rows, six candidate routes, shared-weather copies and source hashes.
- Builder/solver: [recovery_model.py](../research/system_costs/recovery_model.py).
- Independent numerical checks: [check_recovery.py](../research/system_costs/check_recovery.py).
- Results: [results/recovery](../research/system_costs/results/recovery) — scenario networks, decisions, costs, validations and figures.

```bash
python research/system_costs/recovery_model.py
python research/system_costs/check_recovery.py
python research/system_costs/recovery_analysis.py
python research/system_costs/build_notebook.py
python research/system_costs/run_notebook.py --kernel pypsa
```

The solver target is a relative mixed-integer gap of 0.0001 (0.01%). Status and achieved bound/gap are exported. Every year has 8,760 chronological hours, not weighted representative days. Input/output fingerprints permit checked offline reuse. `--force` re-solves. Changing inputs invalidates the cache. Exported PyPSA NetCDF files do not preserve custom constraints: use the builder to rerun; decision CSVs preserve their solutions separately.

Checks reconstruct hourly balance at every bus, battery chronology and limits, service equality, binary decisions, graph connectivity, shared capacity, diesel budgets, repair budgets, lifecycle cost, monotonicity of nested recovery cases, and the zero-budget limiting case. This is numerical validation within the candidate design set; source prices, operational demand, damage and engineering remain unvalidated.

## Results of the saved run

| Recovery condition | Grid connections | Mini-grid connections | Standalone connections | Equivalent annual system cost, USD/year | Initial repair spend, USD |
|---|---:|---:|---:|---:|---:|
| Constrained | 0 | 481 | 399 | 312,318 | 0 |
| Partial | 677 | 0 | 203 | 300,650 | 16,649 |
| Broad | 880 | 0 | 0 | 235,152 | 40,409 |

These counts are potential connections in the four source clusters. Constrained recovery selects a mini-grid at Kubbaka and standalone supply at the other three clusters. Partial recovery repairs the common feeder and builds the S1–S3 route, connecting Al Kurumuk and Kubbaka; Radona and Location #10663 remain standalone. Broad recovery repairs both candidate assets and builds S1–S2, S2–S3 and S2–S4, connecting all four clusters. The full available repair allowance need not be spent.

The broad case uses approximately 50.9 kWp of hub PV and no settlement battery or diesel, conditional on its continuously available upstream supply. This is not evidence that storage is unnecessary under real outages. Partial recovery uses approximately 448 kWh of hub battery energy alongside the standalone systems.

All three saved MIP gaps are zero at solver precision. Independent checks pass for 105,120 settlement-service hours across the three cases, eight off-grid designs, connected routes, storage chronology, transfer limits, fuel limits, repair budgets and reconstructed lifecycle costs. Costs include the assumed separate existing-load block. Improved external supply is a scenario condition, not a fully costed national reconstruction intervention.

## Path to a national study

Extend geographic coverage and candidate shared backbones, distinguish previously connected loads from new access, and connect regional interfaces to the 2022-based generation/transmission investment model. Do not multiply this four-site budget to obtain a Sudan budget. These results do not yet establish national technology shares, real damaged assets to repair, or a construction-ready route plan. Empirical evidence can refine the model later without stopping conditional modelling now.

Sources: [World Bank Group / VIDA DRE Atlas, CC BY 4.0](https://energydata.info/dataset/sudan-distributed-renewable-energy-dre); [NASA POWER hourly API](https://power.larc.nasa.gov/docs/services/api/temporal/hourly/); [PyPSA 1.0.6 custom constraints](https://docs.pypsa.org/v1.0.6/user-guide/optimization/custom-constraints/). See the repository's existing source registers for weather retrieval metadata and cost evidence.
