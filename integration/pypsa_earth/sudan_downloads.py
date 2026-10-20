"""Verified-TLS, streaming downloads with retries and a persistent URL cache.

Used by the local Earth download repair. No credentials or TLS settings changed.
Cache entries become complete only after a successful, length-checked transfer.
"""
import hashlib
import logging
import os
from pathlib import Path
import shutil
import time
import requests

logger = logging.getLogger(__name__)


def retrieve(url, file, data=None, headers=None, disable_progress=False, roundto=1):
    target = Path(file)
    target.parent.mkdir(parents=True, exist_ok=True)
    # POST requests can depend on inputs; do not cache them by URL alone.
    cache = Path.cwd() / ".cache/sudan-downloads"
    cache.mkdir(parents=True, exist_ok=True)
    key = hashlib.sha256(url.encode()).hexdigest()
    complete = cache / (key + ".complete")
    partial = cache / (key + ".part")
    if data is None and complete.is_file() and complete.stat().st_size > 0:
        shutil.copyfile(complete, target)
        logger.info("Using completed download cache: %s", url)
        return
    for attempt in range(1, 4):
        try:
            method = requests.get if data is None else requests.post
            kwargs = dict(headers=headers, stream=True, timeout=(30, 120))
            if data is not None:
                kwargs["data"] = data
            with method(url, **kwargs) as response:
                response.raise_for_status()
                length = response.headers.get("Content-Length")
                count = 0
                with partial.open("wb") as stream:
                    for chunk in response.iter_content(chunk_size=1024 * 1024):
                        if chunk:
                            stream.write(chunk)
                            count += len(chunk)
                if not count:
                    raise IOError("Empty response body")
                if length and not response.headers.get("Content-Encoding"):
                    if count != int(length):
                        raise IOError(f"Incomplete body: {count} of {length} bytes")
            os.replace(partial, complete)
            shutil.copyfile(complete, target)
            if data is not None:
                complete.unlink()
            return
        except (requests.RequestException, OSError) as error:
            logger.warning("Download attempt %d/3 failed for %s: %s: %s",
                           attempt, url, type(error).__name__, error)
            if attempt == 3:
                raise
            time.sleep(2 ** attempt)
