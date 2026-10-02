"""Follow-ups: for applications still at applied after `followup_after_days` (10) whose posting is still up, a short
note to send a recruiter or the hiring manager, drafted from the posting and the resume. Drafts only: nothing is sent.

Made by radar/agents.py with the API or a coding assistant; kept in .cache/ui/followups.json. A draft leaves the list
when it is marked sent or dismissed, when the application moves on, or when the watcher finds its posting closed."""

import json
from datetime import datetime, timedelta
from pathlib import Path

from radar import applications, facts, owner, store, watch
from tailoring import resumes

STATE = Path(".cache/ui/followups.json")
AFTER_DAYS = 10
RULES = """Write a short follow-up for one job application that has had no reply, for the person to send themselves.
Use only the posting and the resume. No number that is not in them, no visa or sponsorship mention, no em dashes.
linkedin_note: under 300 characters, to a recruiter or the hiring manager for this role: the role and its requisition
id, one specific reason the person fits from the resume, and a polite ask to be considered. No greeting by name.
email_subject: under 70 characters.
email_body: 60 to 110 words with the same content, plain and warm, ending with the sign-off {name}.
search_hint: what to type into LinkedIn search to find the recruiter or hiring manager for this role, under 60
characters, for example "Contoso recruiter data science"."""
FIELDS = ("linkedin_note", "email_subject", "email_body", "search_hint")
SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {k: {"type": "string"} for k in FIELDS},
    "required": list(FIELDS),
}


def load():
    return json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {}


def save(state):
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(state, indent=1), encoding="utf-8")


def due(cfg=None, every=False, today=None):
    """Applications quiet for the set number of days, oldest first, whose posting is not known to be closed and that
    have no draft yet; with every, all applications, for a draft asked for by name."""
    days = ((cfg or {}).get("agents") or {}).get("followup_after_days", AFTER_DAYS)
    cutoff = ((today or datetime.now()) - timedelta(days=days)).strftime("%Y-%m-%d")
    made, watched = load(), watch.load()["postings"]
    out = []
    for a in sorted(applications.rows(), key=lambda a: a["date"]):
        key = f"{a['company']}|{a['req_id']}"
        closed = (watched.get(key) or {}).get("status") == "closed"
        if every or (a["status"] == "applied" and a["date"][:10] <= cutoff and not closed and key not in made):
            fields = {k: a[k] for k in ("company", "req_id", "title")}
            out.append({"key": key, "applied": a["date"][:10]} | fields)
    return out


def packet(item, jobs=None):
    j = {store.key(x): x for x in (store.load() if jobs is None else jobs)}.get(item["key"]) or {}
    bases = resumes.bases()
    resume = bases.get((j.get("verdict") or {}).get("recommended_resume")) or bases["experienced"]
    return item | {"posting": (j.get("description") or "")[:6000], "resume": resume[:6000]}


def prompt(p):
    return (
        f"APPLICATION: {p['title']} at {p['company']}, requisition {p['req_id']}, applied {p['applied']}, no reply "
        f"since.\n\nPOSTING:\n{p['posting'] or '(not stored: work from the title and the company)'}\n\n"
        f"RESUME:\n{p['resume']}\n\nWrite the follow-up."
    )


def rules():
    return RULES.replace("{name}", owner.signature(short=True))


def check(answer):
    """The lengths the schema cannot say, so a note that would not fit LinkedIn's limit goes back for a rewrite."""
    found = []
    if len(answer["linkedin_note"]) >= 300:
        found.append(f"linkedin_note is {len(answer['linkedin_note'])} characters; it must stay under 300")
    words = len(answer["email_body"].split())
    if not 40 <= words <= 140:
        found.append(f"email_body is {words} words; write 60 to 110")
    return found


def store_answer(item, answer, by, p, problems=()):
    clean, notes = facts.lock(answer, [p["posting"], p["resume"], p["req_id"], p["title"]])
    state = load()
    state[item["key"]] = {k: item[k] for k in ("company", "req_id", "title", "applied")} | {
        "made": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "by": by,
        "draft": clean,
        "notes": list(problems) + notes,
        "done": None,
    }
    save(state)


def done(key, how="sent"):
    """Take a draft off the list once it is sent, or dismissed. False when there is no such draft."""
    state = load()
    if key not in state or how not in ("sent", "dismissed"):
        return False
    state[key]["done"] = f"{how} {datetime.now().strftime('%Y-%m-%d')}"
    save(state)
    return True


def report():
    """Drafts still worth sending: not done, the application still at applied, its posting not known to be closed."""
    status = {f"{a['company']}|{a['req_id']}": a["status"] for a in applications.rows()}
    watched = watch.load()["postings"]
    live = [
        dict(v, key=k)
        for k, v in load().items()
        if not v.get("done") and status.get(k) == "applied" and (watched.get(k) or {}).get("status") != "closed"
    ]
    return {"items": sorted(live, key=lambda r: r["applied"]), "due": len(due())}
