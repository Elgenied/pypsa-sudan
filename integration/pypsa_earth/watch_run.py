"""Observe one already-running WSL workflow and write a small local status page.

No scheduling, automatic retries, new solver launches or credential access.
Exits when the observed process exits. Generated status is local runtime state.
"""
import argparse
from datetime import datetime, timezone
import html
import json
import os
from pathlib import Path
import time


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--earth", type=Path, required=True)
    parser.add_argument("--pid", type=int, required=True)
    parser.add_argument("--output", type=Path, action="append", required=True)
    args = parser.parse_args()
    root = args.earth
    log = root / "logs/sudan-2022-reference/workflow.log"
    result = root / "results/sudan-2022-reference/networks/elec_s_10_ec_lc1.0_3H.nc"
    started = datetime.now(timezone.utc).isoformat()
    proc = Path(f"/proc/{args.pid}")
    # Match process start tick as well as PID to avoid following a reused PID.
    identity = (proc / "stat").read_text().split()[21]
    for out in args.output:
        out.mkdir(parents=True, exist_ok=True)
    while True:
        try:
            alive = (proc / "stat").read_text().split()[21] == identity
        except FileNotFoundError:
            alive = False
        text = log.read_text(errors="replace") if log.exists() else ""
        complete = result.is_file() and "100%) done" in text and "Error in rule" not in text
        state = "running" if alive else ("completed_check_results" if complete else "stopped_needs_inspection")
        progress = [line for line in text.splitlines() if
                    "steps (" in line or line.startswith("rule ") or
                    "Downloading bundle " in line or "Finished job " in line]
        data = {
            "updated_UTC": datetime.now(timezone.utc).isoformat(),
            "observer_started_UTC": started, "workflow_pid": args.pid,
            "state": state, "earth_root": str(root),
            "latest_progress": progress[-8:],
            "temporary_bundle_download_MB": round((root / "tempfile.zip").stat().st_size / 1e6, 1)
            if (root / "tempfile.zip").exists() else None,
            "weather_cutout_exists": (root / "cutouts/sudan-2022-era5.nc").exists(),
            "network_result_exists": result.exists(),
            "result_path": str(result),
            "scope": "2022 fixed-capacity diagnostic dispatch, ten clusters, 3H; not recovery investment results",
            "interpretation": "Completion does not establish scientific validation; inspect fleet, imports and unserved energy.",
        }
        page = f"""<!doctype html><html><head><meta charset="utf-8">
<meta http-equiv="refresh" content="30"><title>Sudan Earth — live run status</title>
<style>body{{font:17px system-ui;max-width:1000px;margin:50px auto;color:#183d48;
background:#f7fafb;padding:20px}} pre{{white-space:pre-wrap;background:white;padding:24px;
border:1px solid #cddfe3;border-radius:12px}} h1{{font-size:32px}}a{{color:#147c83}}</style>
</head><body><h1>Sudan PyPSA-Earth — {html.escape(state.replace('_',' '))}</h1>
<p>Live local status. Refreshes every 30 seconds while this WSL observer is running.</p>
<p><b>Scope:</b> 2022 baseline dispatch · 10 spatial clusters · three-hour averages.
This is not yet the recovery investment study.</p>
<pre>{html.escape(json.dumps(data, indent=2))}</pre>
<p>The workflow downloads inputs, constructs the network and renewable profiles,
then runs HiGHS. A running workflow does not mean the solver has started.</p>
<p>Log in WSL: <code>{html.escape(str(log))}</code></p>
<p>To stop: <code>kill -INT {args.pid}</code>. Keep WSL and the computer running.</p>
</body></html>"""
        for out in args.output:
            for name, content in [("RUN_STATUS.json", json.dumps(data, indent=2)),
                                  ("RUN_STATUS.html", page)]:
                tmp = out / (name + ".tmp")
                tmp.write_text(content, encoding="utf-8")
                os.replace(tmp, out / name)
        if not alive:
            break
        time.sleep(30)


if __name__ == "__main__":
    main()
