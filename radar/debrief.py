"""Interview debrief: after a screen or an interview, the person's own account of it becomes what was asked and how
each answer could be stronger, what the interviewer seemed unsure about, what they promised to send, what to prepare
for the next round, and a thank-you note.

The account is stored first (add); radar/agents.py then writes the debrief with the API or a coding assistant, as for
prep. Every round of an application is kept, in order, in .cache/ui/debriefs.json, and the next prep for that
application reads them (earlier). Numbers must come from the account, the posting or the resume (radar/facts.py)."""

import json
from datetime import datetime
from pathlib import Path

from radar import applications, facts, owner, store
from tailoring import resumes, skills

STATE = Path(".cache/ui/debriefs.json")
MAX_ACCOUNT = 8000
RULES = """You debrief one person right after a recruiter screen or an interview, from their own account of it. Write
to them as "you". Use only their account, the posting, the resume and the profile: never invent what was asked or
said, and never add experience or numbers that the resume and the account do not contain.
summary: two honest sentences on how it went and what the next step depends on.
asked: every question the account mentions, in order. went: strong, okay or weak, judged from how they say they
answered. better: for an okay or weak answer, the stronger answer itself, in their voice as they could say it next
time, two to four sentences drawn from the resume, not advice about it; for a strong one, "".
concerns: what the interviewer seemed unsure about, each with how to address it in the thank-you note or next round.
went_well: what to keep doing. next_round: what to prepare for the next round, specific to this role and team.
owed: anything they promised to send or do, or none.
thank_you_subject: under 70 characters. thank_you_body: 60 to 120 words, warm and specific to one thing discussed,
addressed to the interviewers the account names, or "Hi," when it names none, and signed {name}. No em dashes and no
double hyphens: use commas or full stops."""
WENT = {"type": "string", "enum": ["strong", "okay", "weak"]}
TEXTS = {"type": "array", "items": {"type": "string"}}


def _obj(props):
    return {"type": "object", "additionalProperties": False, "properties": props, "required": list(props)}


S = {"type": "string"}
SCHEMA = _obj(
    {
        "summary": S,
        "asked": {"type": "array", "items": _obj({"question": S, "went": WENT, "better": S})},
        "concerns": {"type": "array", "items": _obj({"concern": S, "address": S})},
        "went_well": TEXTS,
        "next_round": TEXTS,
        "owed": TEXTS,
        "thank_you_subject": S,
        "thank_you_body": S,
    }
)


def load():
    """Every round written or waiting, by application; a missing or unreadable file reads as none."""
    try:
        return json.loads(STATE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def add(company, req_id, account):
    """Keep their account of the latest round, to be debriefed. A second account before the debrief is written adds
    to the first rather than starting another round. False when there is no such application or nothing to keep."""
    account = (account or "").strip()[:MAX_ACCOUNT]
    app = next((a for a in applications.rows() if a["company"] == company and a["req_id"] == req_id), None)
    if not account or app is None:
        return False
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    with store.lock():
        state = load()
        rounds = state.setdefault(f"{company}|{req_id}", [])
        if rounds and rounds[-1].get("debrief") is None:
            rounds[-1]["account"] = (rounds[-1]["account"] + "\n\n" + account)[-MAX_ACCOUNT:]
        else:
            rounds.append({"account": account, "added": now, "stage": app["status"], "debrief": None, "notes": []})
        store.write_json(STATE, state)
    return True


def due(cfg=None, every=False):
    """Applications whose latest account waits for its debrief; with every, any application with an account, so a
    debrief can be written again by name."""
    rounds, out = load(), []
    for a in applications.rows():
        key = f"{a['company']}|{a['req_id']}"
        last = (rounds.get(key) or [None])[-1]
        if last and (every or last.get("debrief") is None):
            fields = {k: a[k] for k in ("company", "req_id", "title", "status")}
            out.append({"key": key, "applied": a["date"][:10], "added": last["added"], "stage": last["stage"]} | fields)
    return out


def choose(found):
    """Of one employer's applications, the one whose account came in last."""
    return max(found, key=lambda i: i["added"], default=None)


def earlier(key, before=None):
    """What earlier debriefs of one application found, as short lines for the next debrief or prep. "" when none."""
    lines = []
    for n, r in enumerate((load().get(key) or [])[:before], 1):
        d = r.get("debrief")
        if d:
            weak = "; ".join(a["question"] for a in d["asked"] if a["went"] != "strong") or "none"
            lines.append(f"Round {n}, the {r['stage']} on {r['added'][:10]}: answers to work on: {weak}.")
            lines += [f"  They seemed unsure: {c['concern']}" for c in d["concerns"]]
            lines += [f"  To prepare: {x}" for x in d["next_round"]]
    return "\n".join(lines)


def packet(item, jobs=None):
    j = {store.key(x): x for x in (store.load() if jobs is None else jobs)}.get(item["key"]) or {}
    bases = resumes.bases()
    rounds = load().get(item["key"]) or []
    return item | {
        "account": rounds[-1]["account"] if rounds else "",
        "earlier": earlier(item["key"], before=-1),
        "posting": (j.get("description") or "")[:8000],
        "resume": (bases.get((j.get("verdict") or {}).get("recommended_resume")) or bases["experienced"])[:8000],
        "profile": resumes.profile_text()[:2000],
        "skills": ", ".join(skills.load()),
    }


def rules():
    return RULES.replace("{name}", owner.signature())


def prompt(p):
    return "\n\n".join(
        [
            f"APPLICATION: {p['title']} at {p['company']}, requisition {p['req_id']}. The round: the {p['stage']}.",
            "THEIR ACCOUNT OF IT:\n" + p["account"],
            "EARLIER ROUNDS:\n" + (p["earlier"] or "(none)"),
            "POSTING:\n" + (p["posting"] or "(not stored: work from the title and the company)"),
            "RESUME:\n" + p["resume"],
            "PROFILE:\n" + p["profile"],
            "CONFIRMED SKILLS:\n" + (p["skills"] or "(none)"),
            "Write the debrief.",
        ]
    )


def check(answer):
    """The note's length, which the schema cannot say."""
    words = len(answer["thank_you_body"].split())
    return [] if 40 <= words <= 160 else [f"thank_you_body is {words} words; write 60 to 120"]


def store_answer(item, answer, by, p, problems=()):
    keys = ("account", "earlier", "posting", "resume", "profile", "skills", "company", "req_id", "title", "added")
    clean, notes = facts.lock(answer, [p[k] for k in keys])
    with store.lock():  # an account added meanwhile stays waiting for its own debrief
        state = load()
        rounds = state.get(item["key"]) or []
        if rounds:
            rounds[-1] |= {"debrief": clean, "made": datetime.now().strftime("%Y-%m-%d %H:%M"), "by": by}
            rounds[-1]["notes"] = list(problems) + notes
            store.write_json(STATE, state)


def report():
    """Every debriefed round, newest first, with its application's names, and how many accounts wait for one."""
    apps = {f"{a['company']}|{a['req_id']}": a for a in applications.rows()}
    items = [
        dict(r, key=k, round=n, company=apps[k]["company"], req_id=apps[k]["req_id"], title=apps[k]["title"])
        for k, rounds in load().items()
        if k in apps
        for n, r in enumerate(rounds, 1)
        if r.get("debrief")
    ]
    waiting = sum(1 for k, rounds in load().items() if k in apps and rounds and rounds[-1].get("debrief") is None)
    return {"items": sorted(items, key=lambda r: r["made"], reverse=True), "waiting": waiting}
