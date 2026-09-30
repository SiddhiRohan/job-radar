"""python -m radar.watch: re-read the posting behind every open application and record what changed.

Closed (the detail record is gone), retitled, pay range changed, or the description rewritten. A closed posting with
no reply is the quiet rejection nobody emails about. State in .cache/ui/watch.json; one request per posting at the
client's 1.5 s gap, only for applications that are not already rejected or at offer."""

import json
import re
import sys
from datetime import datetime
from pathlib import Path

import requests

from radar import applications, boards, salary, store, wd

STATE = Path(".cache/ui/watch.json")
DONE = ("rejected", "offer")


def load():
    return json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {"postings": {}, "last_run": None}


def save(state):
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(state, indent=1), encoding="utf-8")


def fingerprint(text):
    """The description with whitespace and digits normalised, so a date or a counter does not read as a rewrite."""
    return re.sub(r"\d+", "#", re.sub(r"\s+", " ", text or "")).strip().lower()


def compare(job, detail):
    """What differs between the stored posting and a fresh detail record, as short labels."""
    changes = []
    if detail["title"] and detail["title"] != job["title"]:
        changes.append(f"title now: {detail['title']}")
    old_pay, new_pay = salary.extract(job.get("description", "")), salary.extract(detail.get("description", ""))
    if (old_pay or {}).get("text") != (new_pay or {}).get("text"):
        changes.append(
            f"pay now: {(new_pay or {}).get('text', 'not listed')} (was {(old_pay or {}).get('text', 'not listed')})"
        )
    a, b = fingerprint(job.get("description", "")), fingerprint(detail.get("description", ""))
    if a and b and a != b:
        common = sum(1 for x in set(a.split()) if x in set(b.split()))
        if common / max(1, len(set(a.split()))) < 0.8:
            changes.append("description rewritten")
    return changes


def gone(response):
    """Workday answers 404 for a path it never had and 403 "permission denied" (errorCode S22) for a posting that was
    taken down. A 403 without Workday's JSON error body is a block or an outage, not a closure."""
    if response is None:
        return False
    if response.status_code in (404, 410):
        return True
    if response.status_code != 403:
        return False
    try:
        return "errorCode" in response.json()
    except ValueError:
        return False


def check(app, job, company, fetch=wd.fetch_detail, find=boards.find):
    """One posting: {"status": "open"|"closed"|"unknown", "changes": [...]}."""
    if job and company and boards.system(company):  # a board lists every open posting: gone from it means closed
        try:
            match = find(company, job["req_id"])
        except (requests.RequestException, ValueError) as e:
            return {"status": "unknown", "changes": [], "note": str(e)[:80]}
        return (
            {"status": "closed", "changes": []}
            if match is None
            else {"status": "open", "changes": compare(job, match["detail"])}
        )
    if not job or not job.get("detail_path") or not company:
        return {"status": "unknown", "changes": [], "note": "posting not stored"}
    try:
        detail = fetch(company["tenant"], company["shard"], job["detail_path"])
    except requests.HTTPError as e:
        if gone(e.response):
            return {"status": "closed", "changes": []}
        return {
            "status": "unknown",
            "changes": [],
            "note": f"HTTP {e.response.status_code if e.response is not None else '?'}",
        }
    except (requests.RequestException, ValueError) as e:
        return {"status": "unknown", "changes": [], "note": str(e)[:80]}
    return {"status": "open", "changes": compare(job, detail)}


def run(fetch=wd.fetch_detail, find=boards.find):
    """Check every open application; keep first-seen dates for closures and changes."""
    state, today = load(), datetime.now().strftime("%Y-%m-%d")
    jobs = {f"{j['company']}|{j['req_id']}": j for j in store.load()}
    companies = {c["name"]: c for c in json.loads(Path("companies.json").read_text(encoding="utf-8"))}
    counts = {"open": 0, "closed": 0, "changed": 0, "unknown": 0}
    for a in applications.rows():
        if a["status"] in DONE:
            continue
        key = f"{a['company']}|{a['req_id']}"
        r = check(a, jobs.get(key), companies.get(a["company"]), fetch, find)
        rec = state["postings"].setdefault(
            key, {"company": a["company"], "title": a["title"], "applied": a["date"][:10], "changes": []}
        )
        rec.update(status=r["status"], checked=today, note=r.get("note"))
        if r["status"] == "closed" and not rec.get("closed_since"):
            rec["closed_since"] = today
        if r["status"] == "open":
            rec.pop("closed_since", None)
        known = {c["what"] for c in rec["changes"]}
        for what in r["changes"]:
            if what not in known:
                rec["changes"].append({"date": today, "what": what})
        counts[r["status"]] += 1
        counts["changed"] += bool(r["changes"])
    state["last_run"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    save(state)
    return counts


def report(state=None):
    """Closed and changed postings for the page and the assistant, newest closure first."""
    state = state or load()
    rows = [dict(v, key=k) for k, v in state["postings"].items()]
    closed = sorted(
        (r for r in rows if r.get("status") == "closed"), key=lambda r: r.get("closed_since", ""), reverse=True
    )
    changed = [r for r in rows if r.get("changes") and r.get("status") != "closed"]
    return {
        "last_run": state.get("last_run"),
        "open": sum(r.get("status") == "open" for r in rows),
        "closed": closed,
        "changed": changed,
    }


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    c = run()
    print(f"watch: {c['open']} open, {c['closed']} closed, {c['changed']} changed, {c['unknown']} unknown")
