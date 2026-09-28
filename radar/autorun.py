"""Run the radar once a day while the web app is open, and catch up when the machine was off at run time.

config.json: "auto_run" (default true) and "run_time" (default "07:30", local time). The check runs every minute;
a run is due when it is past run_time and the last run started before today's run_time. A failed trigger is not
retried for two hours, so a network outage does not start a run every minute."""

import json
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path

RETRY = timedelta(hours=2)


def run_at(now, cfg):
    hh, _, mm = str(cfg.get("run_time", "07:30")).partition(":")
    return now.replace(hour=int(hh), minute=int(mm or 0), second=0, microsecond=0)


def last_ran(path=Path("last_run.json")):
    """Local time the last run started, from last_run.json, or None."""
    try:
        stamp = json.loads(path.read_text(encoding="utf-8"))["ran_at"]
        return datetime.fromisoformat(stamp).astimezone().replace(tzinfo=None)
    except (OSError, ValueError, KeyError):
        return None


def due(now, cfg, ran):
    if not cfg.get("auto_run", True):
        return False
    at = run_at(now, cfg)
    return now >= at and (ran is None or ran < at)


def check(trigger, state, now=None, cfg_path=Path("config.json"), last=last_ran):
    """One tick: start a run through trigger() when due and not tried recently. Returns what happened."""
    now = now or datetime.now()
    cfg = json.loads(cfg_path.read_text(encoding="utf-8")) if cfg_path.exists() else {}
    if not due(now, cfg, last()):
        return None
    if state.get("tried") and now - state["tried"] < RETRY:
        return None
    state["tried"] = now
    return trigger()


def start(trigger, interval=60):
    """Background thread for the web app; trigger() starts a run and reports whether it did."""
    state = {}

    def loop():
        while True:
            try:
                r = check(trigger, state)
                if r:
                    print(f"autorun {datetime.now():%H:%M}: {r}", flush=True)
            except Exception as e:  # a broken config must not kill the web app
                print(f"autorun: {e}", flush=True)
            time.sleep(interval)

    threading.Thread(target=loop, daemon=True, name="autorun").start()
