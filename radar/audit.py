"""The filter auditor: once a week, a sample of what the rules dropped (radar/dropped.py) and of postings skipped for
sponsorship or years goes to the model, which names the ones the person would have wanted and suggests the narrowest
config.json change that would have kept them. It changes nothing itself: a change is made only when the person
applies it (apply). Written by radar/agents.py with the API or a coding assistant; kept in .cache/ui/audit.json."""

import json
from datetime import datetime, timedelta
from pathlib import Path

from radar import configedit, digest, dropped, store
from tailoring import resumes

STATE = Path(".cache/ui/audit.json")
EVERY_DAYS, MIN_DROPS = 7, 20
SETTINGS = ("title_patterns", "entry_title_patterns", "exclude_seniority", "exclude_domain", "include_override")
RULES = """You audit the filters of one person's job search. Each item is a posting the filters removed before it was
scored, with the rule that removed it and how many postings carried that title. From their profile and the current
settings, judge which ones they would have wanted to see.
summary: two sentences: how the filters are doing, and the one change worth the most.
wanted: only the items they would likely have wanted, by id, each with why in one sentence.
changes: at most four changes that would keep the wanted items without letting in the rest. setting is one of the
listed settings, action add or remove, value the exact entry, keeps the ids it would keep. title_patterns and
entry_title_patterns are regular expressions searched in the title; exclude_seniority and exclude_domain are whole
words; include_override phrases beat both exclude lists. Prefer the narrowest change. Sponsorship and years skips
are fixed rules, not settings: never suggest a change for them, but list one as wanted if the skip looks wrong.
Plain sentences, no em dashes."""


def _obj(props):
    return {"type": "object", "additionalProperties": False, "properties": props, "required": list(props)}


S, TEXTS = {"type": "string"}, {"type": "array", "items": {"type": "string"}}
SETTING, ACTION = {"type": "string", "enum": list(SETTINGS)}, {"type": "string", "enum": ["add", "remove"]}
CHANGE = _obj({"setting": SETTING, "action": ACTION, "value": S, "why": S, "keeps": TEXTS})
SCHEMA = _obj(
    {
        "summary": S,
        "wanted": {"type": "array", "items": _obj({"id": S, "why": S})},
        "changes": {"type": "array", "items": CHANGE},
    }
)


def load():
    try:
        return json.loads(STATE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def due(cfg=None, every=False, today=None):
    """One audit when the last is a week old (audit_every_days) and enough was dropped since; with every, one now."""
    today, last = today or datetime.now(), load().get("made", "")[:10]
    days = ((cfg or {}).get("agents") or {}).get("audit_every_days", EVERY_DAYS)
    since = last or (today - timedelta(days=days)).strftime("%Y-%m-%d")
    fresh = not last or last <= (today - timedelta(days=days)).strftime("%Y-%m-%d")
    if not every and not (fresh and sum(dropped.counts(since).values()) >= MIN_DROPS):
        return []
    return [{"key": f"audit|{today:%Y-%m-%d}", "company": "", "req_id": "", "title": "filter audit", "since": since}]


def choose(found):
    return found[0] if found else None


def skipped(jobs, since, per=10):
    """Stored postings a fixed rule skipped since a day, with the words that decided it."""
    out = []
    for reason, hit, why in (
        ("sponsorship_no", lambda j: j.get("sponsorship") == "no", lambda j: j.get("sponsorship_evidence") or ""),
        ("years_gate", lambda j: j.get("years_gate"), lambda j: f"asks {j.get('years_required')}+ years"),
    ):
        rows = [j for j in jobs if (j.get("first_seen") or "")[:10] >= since and hit(j)][:per]
        out += [dropped.item(j["company"], j, reason) | {"count": 1, "evidence": why(j)[:160]} for j in rows]
    return out


def packet(item, jobs=None):
    items = dropped.sample(item["since"]) + skipped(
        digest.load_jsonl("jobs.jsonl") if jobs is None else jobs, item["since"]
    )
    items = [dict(i, id=f"r{n}") for n, i in enumerate(items, 1)]
    cfg = configedit.load()
    return item | {
        "items": items,
        "settings": {k: cfg.get(k, []) for k in SETTINGS},
        "profile": resumes.profile_text()[:2000],
    }


def rules():
    return RULES


def prompt(p):
    lines = [
        f"{i['id']} | {i['reason']} | {i['count']} posting(s) | {i['title']} | {i['company']}"
        + (f" | {i['evidence']}" if i.get("evidence") else "")
        for i in p["items"]
    ]
    settings = json.dumps(p["settings"], indent=1)
    return f"PROFILE:\n{p['profile']}\n\nSETTINGS:\n{settings}\n\nREMOVED SINCE {p['since']}:\n" + "\n".join(lines)


def check(answer):
    return []


def store_answer(item, answer, by, p, problems=()):
    ids, notes = {i["id"] for i in p["items"]}, list(problems)
    wanted = [w for w in answer["wanted"] if w["id"] in ids]
    notes += [f"{w['id']} is not an item in the sample" for w in answer["wanted"] if w["id"] not in ids]
    changes = []
    for c in answer["changes"][:4]:
        if why := configedit.problem(c, p["settings"]):
            notes.append(f"left out: {why}")
        else:
            changes.append(c)
    record = {"made": datetime.now().strftime("%Y-%m-%d %H:%M"), "by": by, "since": p["since"], "items": p["items"]}
    with store.lock():
        store.write_json(
            STATE,
            record
            | {"summary": answer["summary"], "wanted": wanted, "changes": changes, "notes": notes, "applied": []},
        )


def apply(n):
    """Make suggested change n in config.json, because the person asked. Returns what changed, or why not."""
    with store.lock():
        state = load()
        changes = state.get("changes") or []
        if not 0 <= n < len(changes) or n in state.get("applied", []):
            return "nothing to apply"
        if why := configedit.make(changes[n]):
            return why
        store.write_json(STATE, state | {"applied": state.get("applied", []) + [n]})
    c = changes[n]
    return f"{c['setting']}: {'added' if c['action'] == 'add' else 'removed'} {c['value']}"


def report(today=None):
    """The latest audit with its wanted postings looked up, and what the rules dropped in the last week."""
    state, week = load(), ((today or datetime.now()) - timedelta(days=7)).strftime("%Y-%m-%d")
    by_id = {i["id"]: i for i in state.get("items", [])}
    wanted = [by_id[w["id"]] | {"why": w["why"]} for w in state.get("wanted", []) if w["id"] in by_id]
    keep = ("made", "since", "summary", "changes", "applied", "notes")
    return {k: state.get(k) for k in keep} | {"wanted": wanted, "dropped": dropped.counts(week)}
