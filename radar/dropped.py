"""What the radar's rules dropped before anyone saw it: titles that name no target role, seniority or domain words,
places outside the US. The poll logs each drop here for two weeks (.cache/ui/removed.json), so the filter auditor
(radar/audit.py) can check the rules against what they actually threw away."""

import json
import re
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

from radar import store

LOG = Path(".cache/ui/removed.json")
KEEP_DAYS, CAP = 14, 6000
PER = {"off_target": 25, "seniority": 15, "domain": 10, "non_us": 5}  # distinct titles per rule in a sample
LABELS = {
    "off_target": "title names no target role",
    "seniority": "a seniority word in the title",
    "domain": "a domain word in the title",
    "non_us": "outside the US",
}


def item(company, j, reason):
    """One drop, as poll.py and boards.py log it."""
    fields = {
        "company": company,
        "title": j.get("title", ""),
        "url": j.get("url", ""),
        "location": j.get("location", ""),
    }
    return {"key": f"{company}|{j.get('req_id', '')}", "reason": reason} | fields


def load():
    try:
        return json.loads(LOG.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"items": []}


def record(items, when=None):
    """Add one run's drops: the newest per posting and rule, two weeks of them, at most CAP."""
    day = (when or datetime.now()).strftime("%Y-%m-%d")
    cutoff = ((when or datetime.now()) - timedelta(days=KEEP_DAYS)).strftime("%Y-%m-%d")
    with store.lock():
        kept = {(i["key"], i["reason"]): i for i in load()["items"] if i.get("day", "") >= cutoff}
        kept |= {(i["key"], i["reason"]): i | {"day": day} for i in items}
        rows = sorted(kept.values(), key=lambda i: i["day"], reverse=True)[:CAP]
        store.write_json(LOG, {"items": rows})


def counts(since):
    """How many postings each rule dropped since a day."""
    out = defaultdict(int)
    for i in load()["items"]:
        if i.get("day", "") >= since:
            out[i["reason"]] += 1
    return dict(out)


def sample(since, per=None):
    """The titles each rule dropped most often since a day, one example posting each with how many carried the
    title, so a few dozen lines stand for hundreds of drops."""
    per = PER if per is None else per
    groups = defaultdict(lambda: defaultdict(list))
    for i in load()["items"]:
        if i.get("day", "") >= since and i["reason"] in per:
            groups[i["reason"]][re.sub(r"\s+", " ", i["title"].lower()).strip()].append(i)
    out = []
    for reason in per:
        ranked = sorted(groups[reason].values(), key=lambda rows: (-len(rows), rows[0]["title"]))[: per[reason]]
        out += [dict(rows[0], count=len(rows)) for rows in ranked]
    return out
