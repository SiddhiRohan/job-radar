"""One run at a time, whoever starts it: the web app, the operating system's scheduler, or the command line.

run.py takes the lock for its whole life and releases it at the end, even on failure. A lock older than four hours
is treated as left behind by a machine that shut down mid-run and is taken over."""

import json
import os
import time
from datetime import datetime
from pathlib import Path

LOCK = Path(".cache/run.lock")
STALE_SECONDS = 4 * 3600


def held(now=None):
    return LOCK.exists() and (now or time.time()) - LOCK.stat().st_mtime < STALE_SECONDS


def since():
    """When the current run started, as HH:MM, or "" when nothing holds the lock."""
    try:
        return json.loads(LOCK.read_text(encoding="utf-8")).get("started", "")[11:16]
    except (OSError, ValueError):
        return ""


def acquire():
    """True when this process now holds the lock; False when another live run does."""
    LOCK.parent.mkdir(parents=True, exist_ok=True)
    for _ in range(2):
        try:
            fd = os.open(LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            if held():
                return False
            LOCK.unlink(missing_ok=True)  # stale: the machine went down mid-run
            continue
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump({"pid": os.getpid(), "started": datetime.now().isoformat(timespec="seconds")}, f)
        return True
    return False


def release():
    LOCK.unlink(missing_ok=True)
