"""Interview prep: when an email moves an application to a screen or an interview, a page of preparation for it, from
the stored posting, the fit factor by factor, the resume it was scored against and the employer's sponsorship record.

Made by radar/agents.py with the API or a coding assistant; kept in .cache/ui/prep.json, one per application and
stage, so moving on from a screen to an interview brings a new one. Numbers in it must come from the posting or the
resume: any other is taken out and named in its notes (radar/facts.py)."""

import json
from datetime import datetime
from pathlib import Path

from radar import applications, facts, fit, sponsormap, store
from tailoring import resumes, skills

STATE = Path(".cache/ui/prep.json")
STAGES = ("screen", "interview")
RULES = """You prepare one person for a recruiter screen or an interview for a job they applied to. Write to them as
"you". Use only what is given: the posting, the radar's fit notes, the resume, the profile and the confirmed skills.
Never invent experience, employers, dates, titles or numbers: a story uses only what the resume says, and a result
the resume gives no number for stays without one.
role: two sentences on what the job is and what the team will care about most.
focus: three to five topics they will probe. why: what in the posting makes it likely. evidence: the resume line that
answers it, or "" when the resume shows none.
questions: six to eight likely questions mixing the role's technical core, behavioral and motivation; kind says which.
answer_from: the resume experience to draw on, or how to answer honestly when there is none.
stories: three short stories from the resume, as situation, task, action and result, for the likeliest questions.
gaps: up to three gaps the fit notes name, each with an honest way to address it in the conversation.
ask_them: three questions for the interviewer, specific to this team and posting.
work_authorization: two or three sentences: what the posting says about sponsorship, what the employer's record
shows, and a plain, truthful way to answer the sponsorship question for the status the profile describes, or for
either case when it does not say. It is guidance, not legal advice.
For a screen, weight motivation and fit; for an interview, the technical core. Plain sentences, no em dashes."""


def _obj(props):
    return {"type": "object", "additionalProperties": False, "properties": props, "required": list(props)}


def _strings(*names):
    return {n: {"type": "string"} for n in names}


KIND = {"type": "string", "enum": ["technical", "behavioral", "motivation"]}
SCHEMA = _obj(
    {
        "role": {"type": "string"},
        "focus": {"type": "array", "items": _obj(_strings("topic", "why", "evidence"))},
        "questions": {"type": "array", "items": _obj(_strings("question") | {"kind": KIND} | _strings("answer_from"))},
        "stories": {"type": "array", "items": _obj(_strings("title", "situation", "task", "action", "result"))},
        "gaps": {"type": "array", "items": _obj(_strings("gap", "answer"))},
        "ask_them": {"type": "array", "items": {"type": "string"}},
        "work_authorization": {"type": "string"},
    }
)


def load():
    return json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {}


def due(cfg=None, every=False):
    """Applications at a screen or interview without a prep for that stage; with every, all applications, for a prep
    asked for by name."""
    made = load()
    out = []
    for a in applications.rows():
        key = f"{a['company']}|{a['req_id']}"
        if every or (a["status"] in STAGES and (made.get(key) or {}).get("stage") != a["status"]):
            fields = {k: a[k] for k in ("company", "req_id", "title")}
            out.append({"key": key, "stage": a["status"], "applied": a["date"][:10]} | fields)
    return out


def packet(item, jobs=None, recs=None):
    """Everything the prep is written from: the stored posting, its fit, its sponsorship, one resume, the profile."""
    j = {store.key(x): x for x in (store.load() if jobs is None else jobs)}.get(item["key"]) or {}
    v = j.get("verdict") or {}
    bases = resumes.bases()
    resume = bases.get(v.get("recommended_resume")) or bases["experienced"]
    notes = [
        f"- {f['factor']} ({f['verdict']}): posting asks {f['posting'] or 'nothing specific'}; resume shows "
        f"{f['resume'] or 'nothing'}" + (f"; {f['note']}" if f["note"] else "")
        for f in fit.model_factors(v)
    ]
    rec = (sponsormap.records() if recs is None else recs).get(item["company"]) or {}
    said = j.get("sponsorship_evidence") or v.get("sponsorship_evidence")
    sponsorship = f"The posting reads {j.get('sponsorship') or 'unknown'}" + (f': "{said}"' if said else "")
    sponsorship += f". The employer default is {sponsormap.default_label(rec.get('default'))}"
    sponsorship += (f" ({rec['source']})" if rec.get("source") else "") + (
        f"; H-1B filings: {rec['filings']}." if rec.get("filings") else "."
    )
    return item | {
        "posting": (j.get("description") or "")[:9000],
        "fit": "\n".join(notes),
        "sponsorship": sponsorship,
        "resume": resume[:9000],
        "profile": resumes.profile_text()[:3000],
        "skills": ", ".join(skills.load()),
    }


def rules():
    return RULES


def prompt(p):
    return "\n\n".join(
        [
            f"APPLICATION: {p['title']} at {p['company']}, requisition {p['req_id']}, applied {p['applied']}, "
            + (
                f"now at the {p['stage']} stage."
                if p["stage"] in STAGES
                else "no reply yet: prepare for a first screen."
            ),
            "POSTING:\n" + (p["posting"] or "(not stored: work from the title and the company)"),
            "FIT NOTES FROM THE RADAR:\n" + (p["fit"] or "(none)"),
            "SPONSORSHIP:\n" + p["sponsorship"],
            "RESUME:\n" + p["resume"],
            "PROFILE:\n" + p["profile"],
            "CONFIRMED SKILLS:\n" + (p["skills"] or "(none)"),
            "Write the prep.",
        ]
    )


def check(answer):
    """What the schema cannot say: enough questions and at least one story to practise with."""
    found = [] if len(answer["questions"]) >= 4 else ["questions should hold six to eight questions"]
    return found + ([] if answer["stories"] else ["stories should hold three stories from the resume"])


def store_answer(item, answer, by, p, problems=()):
    keys = ("posting", "fit", "sponsorship", "resume", "profile", "skills", "req_id", "title", "applied")
    sources = [p[k] for k in keys]
    clean, notes = facts.lock(answer, sources)
    state = load()
    state[item["key"]] = {k: item[k] for k in ("company", "req_id", "title", "stage")} | {
        "made": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "by": by,
        "prep": clean,
        "notes": list(problems) + notes,
    }
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(state, indent=1), encoding="utf-8")


def report():
    """Every prep, newest first, with the application's current status, and how many applications wait for one."""
    status = {f"{a['company']}|{a['req_id']}": a["status"] for a in applications.rows()}
    items = [dict(v, key=k, status=status.get(k, "")) for k, v in load().items()]
    return {"items": sorted(items, key=lambda r: r["made"], reverse=True), "due": len(due())}
