"""python -m radar.brief: the morning brief. Which postings to apply to first, what changed since the last brief,
which applications have gone quiet, what the agents wrote, and one thing the rejections suggest.

Built only from what the run already wrote (jobs.jsonl, applications.md, the mail and watch state), so it costs no
model call. The run writes it last; the web app, the assistant and the terminal all read the same note."""

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

from radar import agentview, applications, digest, mail, patterns, salary, watch

STATE = Path(".cache/ui/brief.json")
QUIET_DAYS = 10


def rank(j):
    """Best fit first; then postings that can sponsor, then the one whose factors meet more of the posting, then
    stated pay, then newest."""
    pay = 1 if salary.extract(j.get("description", "")) else 0
    meets = sum(f.get("verdict") == "meets" for f in (j.get("verdict") or {}).get("factors") or [])
    return (digest.best(j), 1 if digest.sponsors(j) else 0, meets, pay, -(j.get("posted_days_ago") or 0))


def reason(j):
    """One line on why: the first gap the fit names, else the start of the model's why."""
    v = j.get("verdict") or {}
    gaps = [f for f in v.get("factors") or [] if f.get("verdict") != "meets"]
    if gaps:
        g = gaps[0]
        return f"{g['factor']}: {g.get('note') or g.get('posting') or g['verdict']}"[:140]
    return (v.get("why") or "").split(". ")[0][:140]


def picks(jobs, day, n=3):
    s = digest.sections([j for j in jobs if j.get("first_seen", "")[:10] == day])
    best = sorted(s["apply"] + s["entry"], key=rank, reverse=True)[:n]
    out = []
    for j in best:
        v, pay = j.get("verdict") or {}, salary.extract(j.get("description", ""))
        out.append(
            {
                "company": j["company"],
                "title": j["title"],
                "req_id": j["req_id"],
                "url": j.get("url", ""),
                "fit": f"E{v.get('score_entry', '-')}/X{v.get('score_experienced', '-')}",
                "pay": pay["text"] if pay else "",
                "reason": reason(j),
            }
        )
    return out


def quiet(apps, watched, today, n=3):
    """Applications still at applied after QUIET_DAYS, oldest first, whose posting is not known to be closed: a
    closed one is reported once under closures, and a follow-up to a filled role is wasted."""
    cutoff = (today - timedelta(days=QUIET_DAYS)).strftime("%Y-%m-%d")
    out = []
    for a in sorted(
        (a for a in apps if a["status"] == "applied" and a["date"][:10] <= cutoff), key=lambda a: a["date"]
    ):
        status = (watched.get(f"{a['company']}|{a['req_id']}") or {}).get("status", "unknown")
        if status != "closed":
            out.append({"company": a["company"], "title": a["title"], "applied": a["date"][:10], "posting": status})
    return out[:n]


def build(now=None, jobs=None):
    now = now or datetime.now()
    jobs = digest.load_jsonl("jobs.jsonl") if jobs is None else jobs
    since = load().get("made_at", (now - timedelta(days=1)).strftime("%Y-%m-%d %H:%M"))
    day = max((j.get("first_seen", "")[:10] for j in jobs), default=now.strftime("%Y-%m-%d"))
    m, w = mail.load(), watch.load()
    moved = [
        {"company": e["company"], "status": e["status"], "from": e.get("from_status", "")}
        for e in m["events"]
        if (e.get("date") or "") >= since
    ]
    closed = [
        {"company": r["company"], "title": r["title"]}
        for r in watch.report(w)["closed"]
        if (r.get("closed_since") or "") >= since[:10]
    ]
    found = patterns.analyse()
    top = next((f for f in found["findings"] if f["lift"] > 0), None) if found["enough_data"] else None
    return {
        "made_at": now.strftime("%Y-%m-%d %H:%M"),
        "day": day,
        "picks": picks(jobs, day),
        "moved": moved,
        "closed": closed,
        "quiet": quiet(applications.rows(), w.get("postings", {}), now),
        "agents": agentview.news(since),
        "suggestion": (
            f"Rejections cluster where {top['dimension'].lower()} is {top['bucket']}: {top['rejected']} of "
            f"{top['applied']} rejected, against {round(100 * found['overall_rate'])}% overall."
            if top
            else ""
        ),
    }


def text(b):
    """The brief as short plain lines, for the terminal, the digest folder and the assistant."""
    out = [f"Morning brief, {b['day']}"]
    if b["picks"]:
        out.append("Apply first:")
        for p in b["picks"]:
            pay = f" | {p['pay']}" if p["pay"] else ""
            out += [f"  {p['company']} | {p['title']} | {p['fit']}{pay}", f"    {p['reason']}"]
    else:
        out.append("Apply first: nothing new scored 4, or 3 for an entry-level title.")
    out += [f"Moved: {x['company']} {x['from']} to {x['status']}" for x in b["moved"]]
    out += [f"Closed: {x['company']}, {x['title']}" for x in b["closed"]]
    out += [f"Quiet since {x['applied']}: {x['company']}, {x['title']} (posting {x['posting']})" for x in b["quiet"]]
    out += [f"Agents: {x}" for x in b.get("agents", [])]
    if b["suggestion"]:
        out.append("Pattern: " + b["suggestion"])
    return "\n".join(out)


def load():
    try:
        return json.loads(STATE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def current():
    """The brief the last run wrote, or one built now when there is none or it is incomplete (an older version)."""
    b = load()
    return b if b.get("day") and "picks" in b else build()


def main():
    b = build()
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(b, indent=1), encoding="utf-8")
    print(text(b))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
