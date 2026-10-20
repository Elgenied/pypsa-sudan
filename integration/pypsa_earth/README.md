# Sudan evidence → PyPSA-Earth

This is the active handover to the Zambia-aligned approach. **It prepares inputs;
it is not a new solved national model or a completed recovery study.**

**Execution update, 20 October 2026:** the user configured CDS credentials and
the native Sudan workflow has been launched. See [the run record](RUN_LAUNCH.md).
Open local `RUN_STATUS.html` for live status; this runtime file is not on GitHub.
The saved handover notebook records the earlier input checks, not solve completion.

Open the executed [handover notebook](Sudan_Earth_Handover.ipynb) or
[HTML reading copy](Sudan_Earth_Handover.html) for the demand chart, candidate
plant-location plot, evidence table and validation summary.

PyPSA-Earth is the national modelling engine. The `pypsa-earth` conda environment
contains its software dependencies; evidence belongs in versioned project files,
not inside the environment. OnSSET remains the complementary electrification branch.

## Locations

- Sudan source repository: `C:/Users/eelqu/Documents/Codex/2026-09-05/i/work/github-publish`
- User-facing mirror: `C:/Users/eelqu/OneDrive - University of Surrey/Desktop/pypsa_sudan`
- Linux engine checkout: `/home/elgenied/Downloads/pypsa-earth`
- Linux environment: `/home/elgenied/miniconda3/envs/pypsa-earth`
- Installed evidence: `pypsa-earth/data/custom/sudan/`
- Run configuration: `pypsa-earth/configs/config.sudan-2022.yaml`

## What goes where

| Evidence | Treatment now | Role in the study |
|---|---|---|
| 2022 national statistics | Copied, checksummed; demand annual balance checked | Baseline capacity, supply, imports and demand benchmarks |
| Existing synthetic hourly demand | Converted to native Earth CSV format, UTC; enabled | Initial national chronological load input, not measured load |
| 2019 inventory and 2012 plant engineering | Explicit identity crosswalk; Earth-format candidate file, disabled | Replace/correct the default fleet after reconciliation |
| August 2024 plant availability | Preserved with source/page/date, not applied to 2022 | Recovery scenario evidence; distinguish fuel/staff shortages from physical damage |
| Network evidence and old diagrams | Preserved as validation evidence | Check OSM routes and voltage; no invented line MW ratings |
| Historical monthly hydro | Retained separately with source | Seasonality cross-check, not observed 2022 reservoir operation |
| Local costs and market quotations | Copied with provenance; not injected into utility costs | OnSSET budgets and selected Sudan cost adjustments after unit/currency/year alignment |
| DRE settlement attributes | Copied for OnSSET, not inserted as thousands of Earth buses | Access options in Northern, River Nile, Khartoum, Gezira, White Nile and Sennar |
| DRE security categories | Preserved as historical 2020–22 exposure | Context only, not post-war damage fractions or present security |

The plant candidate file is deliberately incomplete. It has coordinates from the
2012 report for eleven matched entries in the 2019 inventory. Its nameplate MW
must not be forced to match national **net** MW by silently scaling each plant.
All planned-only entries remain excluded from candidates. Fleet replacement is
disabled; Earth currently retains its default powerplantmatching fleet.

## Demand boundary

2022 reference: **13,261 GWh end-use + 3,652 GWh aggregate losses = 16,913 GWh
sent-out requirement = 16,031 GWh net generation + 882 GWh imports.**
The consumption statistic includes an UNSD estimate. The profile's hourly shape
is synthetic, not GEGIS or a utility measurement. `source: gegis` selects Earth's
standard semicolon-CSV reader only.

The source clock is local UTC+2. The exporter shifts the periodic synthetic
template by two hours into UTC (wrapping at year-end). The native `3H` aggregation
averages consecutive hours and retains duration weights: 2,920 steps, 8,760 hours.
Do not add the same aggregate losses again elsewhere. Future recovery scenarios
may change the loss assumption, but should label that as a scenario change.

Earth's default spatial load allocation uses population/GDP proxies, not the
previous notebook's assumed regional shares. Validate this allocation before
interpreting regional recommendations.

## Reproduce in WSL

```bash
source /home/elgenied/miniconda3/etc/profile.d/conda.sh
conda activate pypsa-earth
SUDAN_REPO=/mnt/c/Users/eelqu/Documents/Codex/2026-09-05/i/work/github-publish
python "$SUDAN_REPO/integration/pypsa_earth/prepare.py" \
  --earth /home/elgenied/Downloads/pypsa-earth
cd /home/elgenied/Downloads/pypsa-earth
python "$SUDAN_REPO/integration/pypsa_earth/validate.py" --earth "$PWD"
snakemake --configfile configs/config.sudan-2022.yaml --cores 2 \
  --dry-run solve_all_networks
```

Staging does not change `config.yaml` or upstream scripts. A receipt records copied
file hashes. It refuses to overwrite unrecognised edits to staged files.

## Baseline configuration and remaining work

The diagnostic baseline is Sudan-wide, ten spatial clusters, full-year 2022,
three-hour aggregation, no CO2 cap, HiGHS, and fixed existing capacity. The
2020 technology-data vintage supplies provisional operating costs; these are
not a calibrated Sudan financial case. Ten clusters are a starting resolution,
not proof that every important corridor survives aggregation.

The native cost-retrieval rule has run successfully and downloaded
`resources/sudan-2022-reference/costs_2020.csv`. Input checks and the full workflow
dry-run pass; [validation.json](validation/validation.json) records versions,
checks and the cost file hash. This does not certify the cost assumptions.

Before a meaningful baseline solve:

1. Obtain the full 2022 ERA5 cutout. CDS credentials have now been configured
   privately and a test request was accepted. Actual retrieval still depends on
   the server queue and applicable dataset access. Existing NASA POWER point profiles are useful
   cross-checks but are not a replacement for an atlite weather cutout.
2. Retrieve standard geography/resource inputs and build the OSM network. These
   are present-day open-data routes, not a certified 2022 or post-war asset register.
3. Reconcile the plant inventory, renewable installed capacities, hydro energy
   and storage assumptions; compare the built network against the national totals.
4. Represent external supply explicitly: the reference has 882 GWh imports. An
   SD-only network with no import supply is not a matched 2022 reference.

Then add the three agreed recovery conditions to the **same** validated baseline:
limited, targeted and broad restoration. Map each assumed damaged/restorable
asset onto actual network IDs; distinguish restored MW, fuel availability,
repair expenditure and new-build expenditure. Standard transmission expansion
costs are not automatically rehabilitation costs. An asset availability change
alone is an exogenous scenario, not an economically optimized repair decision.

Run OnSSET separately with consistent service, currency/year and recovery
definitions. Its outputs are grid extension / mini-grid / standalone maps.
Earth supplies national system results and boundary information. Do not add
their cost totals without reconciling overlapping generation/network spending.

## Reference

This data/configuration layer follows the organisation of
[pypsa-zm-data](https://github.com/pypsa-meets-earth/pypsa-zm-data).
The native custom demand interface is documented in
[PyPSA-Earth basic setup](https://pypsa-earth.readthedocs.io/en/latest/user-guide/customization/basic-setup/).
Exact compatibility is checked against the locally installed code, not assumed
from a different documentation version.
