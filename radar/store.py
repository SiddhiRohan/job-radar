"""jobs.jsonl and seen.json access that is safe when two runs overlap: one row per company|req_id, ever."""

import json
import os
import time
from contextlib import contextmanager
from pathlib import Path

JOBS, SEEN, LOCK = Path("jobs.jsonl"), Path("seen.json"), Path(".cache/jobs.lock")


def key(j):
    return f"{j['company']}|{j['req_id']}"


def _scored(j):
    return "score_entry" in (j.get("verdict") or {})


def dedupe(rows):
    """First occurrence wins its place; a scored copy replaces an unscored one."""
    out = {}
    for j in rows:
        k = key(j)
        if k not in out or (_scored(j) and not _scored(out[k])):
            out[k] = j if k not in out else {**j, "first_seen": out[k].get("first_seen", j.get("first_seen"))}
    return list(out.values())


def load():
    if not JOBS.exists():
        return []
    return dedupe(json.loads(line) for line in JOBS.read_text(encoding="utf-8").splitlines() if line.strip())


@contextmanager
def lock(wait=30, stale=120):
    """Held only for the few milliseconds of a write, so a second run is never blocked, only serialised."""
    LOCK.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.time() + wait
    while True:
        try:
            os.close(os.open(LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY))
            break
        except FileExistsError:
            if time.time() - LOCK.stat().st_mtime > stale or time.time() > deadline:
                LOCK.unlink(missing_ok=True)
            time.sleep(0.2)
    try:
        yield
    finally:
        LOCK.unlink(missing_ok=True)


def append_new(rows, seen_keys=()):
    """Append only rows whose key is not on disk yet; merge seen.json. Returns the rows actually written."""
    with lock():
        have = {key(j) for j in load()}
        fresh = [j for j in dedupe(rows) if key(j) not in have]
        with JOBS.open("a", encoding="utf-8") as f:
            for j in fresh:
                f.write(json.dumps(j) + "\n")
        seen = set(json.loads(SEEN.read_text(encoding="utf-8"))) if SEEN.exists() else set()
        SEEN.write_text(json.dumps(sorted(seen | set(seen_keys) | have), indent=0), encoding="utf-8")
    return fresh


def save(jobs):
    """Rewrite the file from memory, keeping any rows another run appended since we loaded."""
    with lock():
        mine = {key(j) for j in jobs}
        merged = dedupe(list(jobs) + [j for j in load() if key(j) not in mine])
        tmp = JOBS.with_suffix(".tmp")
        tmp.write_text("".join(json.dumps(j) + "\n" for j in merged), encoding="utf-8")
        tmp.replace(JOBS)
    return merged
