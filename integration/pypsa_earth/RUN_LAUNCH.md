# First native Sudan Earth workflow launched

20 October 2026. The user configured CDS credentials privately in WSL and
requested execution. A CDS client initialized successfully, and a small
2022 ERA5 request was accepted by the server. Credentials are not stored here.

The actual workflow was started with:

```bash
source /home/elgenied/miniconda3/etc/profile.d/conda.sh
conda activate pypsa-earth
cd /home/elgenied/Downloads/pypsa-earth
snakemake --configfile configs/config.sudan-2022.yaml \
  --cores 4 --resources mem_mb=45000 --rerun-incomplete solve_all_networks \
  > logs/sudan-2022-reference/workflow.log 2>&1
```

Sudan's OpenStreetMap extraction completed. Initial preparation downloads the
standard global input bundle (approximately 6.46 GB compressed), other resource
datasets and then builds the weather profiles/network before HiGHS runs.
**A workflow launch is not a completed optimization.**

Local `RUN_STATUS.html` and `RUN_STATUS.json` are refreshed every 30 seconds by
`watch_run.py` while this process is alive; they are intentionally excluded from
Git. The observer does not launch new jobs, retry failures or schedule future
runs. It reports a stopped process for inspection if execution fails.
Keep the computer and WSL running.

## Why 2022 weather rather than 2013?

2013 is the standard prebuilt weather-year option in PyPSA-Earth. It is not a
requirement of PyPSA, nor does the existence of a bundle establish that 2013 is
Sudan's most representative weather year. See the official
[weather setup documentation](https://pypsa-earth.readthedocs.io/en/latest/user-guide/customization/basic-setup/).

For this first run we retain:

- **System/demand reference:** 2022.
- **Weather chronology:** 2022.
- **Dispatch resolution:** consecutive three-hour averages.
- **Initial investment setting:** existing capacity fixed; diagnostic dispatch.

A study can instead combine the 2022 system with 2013 weather if it explicitly
states that distinction and aligns the demand/weather clocks. There is no need
to change years merely because 2013 is the default. A single selected weather
year is not a multi-year robustness test.

## How to interpret the eventual output

The baseline still uses the default Earth fleet, generic operating-cost inputs,
proxy regional demand and an SD-only network without the separately documented
882 GWh import contribution. These are recorded calibration gaps. Load shedding
is enabled as an expensive feasibility option, so an optimal solver status
does not establish adequate electricity supply.

Inspect unserved energy, national energy/capacity totals, hydro behaviour,
isolated buses and border supply before interpreting the result. This first
run is not the three-scenario rehabilitation investment study. Its purpose is
to get the standard national workflow running and expose concrete baseline
corrections on the built network.
