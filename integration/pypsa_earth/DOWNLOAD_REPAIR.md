# Download failure diagnosis and local repair

Checked 20 October 2026 after the first workflow stopped during bundle retrieval.

## Findings

1. Seven HydroBASINS downloads left zero-byte ZIPs. The downloader caught every
   exception without recording its type/message. It then attempted to merge all
   basin shapefiles, including files that had never been extracted. That merge
   produced the fatal missing-African-shapefile exception.
2. The Protected Planet downloader tried November, October, September and August
   2026. It starts with the next month and hides the transfer exceptions. The
   October URL currently returns HTTP 200 and advertises a 4,682,783,045-byte file.
   Therefore the evidence does not establish a permanently broken source URL.
3. The separate CDS preflight request was accepted and completed on the server,
   but its result-file transfer failed with `SSLEOFError`. A later retry of that
   same result succeeded and xarray opened the downloaded NetCDF. Credentials
   and dataset access worked in this test.
4. Because all bundles are outputs of one Snakemake job, its default failure
   cleanup removed even the successfully downloaded declared outputs. The
   large common bundle must be retrieved again on this restart.

**Limits of the diagnosis:** the exact original HydroBASINS and Protected Planet
HTTP/TLS errors cannot be recovered from logs that suppressed them. Transient
connection problems are plausible, but are not proven to be the cause of every
failed transfer. A system-curl certificate-chain check also failed against the
CDS object host while requests using the environment's certifi bundle succeeded.
TLS verification remains enabled.

## Applied repair

`install_download_repair.py` applies small local edits to the inspected Earth
checkout and keeps original source copies under
`.cache/sudan-download-repair-originals/`:

- Route `progress_retrieve` through `sudan_downloads.py`: streaming, verified TLS,
  three attempts with backoff, explicit error details and response-length checks.
- Keep completed URL-keyed downloads in `.cache/sudan-downloads/` so retries of
  the workflow can reuse them. Partial files never count as complete. Individual
  transfer retries currently restart the transfer; they do not resume byte ranges.
- Report failures and skip the basin merge when the hydro bundle has failed.
- Raise an explicit error listing missing required bundles.
- Begin Protected Planet date selection with the current month.
- Launch Snakemake with `--keep-incomplete --rerun-incomplete`, preserving
  downloads for inspection/reuse. Preserved files still require validation.

The restarted shell also sets `REQUESTS_CA_BUNDLE` and `SSL_CERT_FILE` to the
installed environment's certifi CA bundle. No credential changes or certificate
verification bypasses were made. Original tutorial-file deletion remains intact.

## Verification

- Patched Python modules compile.
- African level-6 ZIP downloaded and passed its ZIP CRC test.
- Its shapefile opened with 3,597 features.
- Completed CDS test result opened in xarray: one time step and a 2×2 grid.
- Source HEAD checks succeeded for both Africa HydroBASINS and October WDPA.

The full workflow was restarted. This document records the repair and targeted
checks, not completion of all downloads or a successful optimization. The local
`RUN_STATUS.html` and `logs/sudan-2022-reference/workflow.log` show current progress.

## Reapply / resume

```bash
source /home/elgenied/miniconda3/etc/profile.d/conda.sh
conda activate pypsa-earth
SUDAN_REPO=/mnt/c/Users/eelqu/Documents/Codex/2026-09-05/i/work/github-publish
python "$SUDAN_REPO/integration/pypsa_earth/install_download_repair.py" \
  --earth /home/elgenied/Downloads/pypsa-earth
cd /home/elgenied/Downloads/pypsa-earth
export REQUESTS_CA_BUNDLE=/home/elgenied/miniconda3/envs/pypsa-earth/lib/python3.11/site-packages/certifi/cacert.pem
export SSL_CERT_FILE="$REQUESTS_CA_BUNDLE"
snakemake --configfile configs/config.sudan-2022.yaml --cores 4 \
  --resources mem_mb=45000 --rerun-incomplete --keep-incomplete solve_all_networks
```

These are project-specific local patches, not changes pushed to the upstream
PyPSA-Earth repository. Review compatibility before upgrading that checkout.
