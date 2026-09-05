"""Re-fetch the exact public inputs recorded in the download manifest.

Cached files are hash-checked. Changed upstream bytes fail verification instead of
silently changing the study. This script needs internet access only for missing files.
"""
from pathlib import Path
import hashlib
import json
import requests

ROOT = Path(__file__).resolve().parents[1]


def main():
    raw = ROOT / "data/raw"
    manifest = json.loads((raw / "download_manifest.json").read_text())
    for entry in manifest:
        destination = raw / entry["file"]
        if destination.exists():
            content = destination.read_bytes()
        else:
            response = requests.get(entry["url"], timeout=120)
            response.raise_for_status()
            content = response.content
        actual = hashlib.sha256(content).hexdigest()
        if actual != entry["sha256"]:
            raise RuntimeError(f"Source changed: {entry['file']}. Review the new source and version the manifest before using it.")
        if not destination.exists():
            destination.write_bytes(content)
        print(f"VERIFIED {entry['file']}: {len(content):,} bytes")


if __name__ == "__main__":
    main()
