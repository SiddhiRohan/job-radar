"""Leads for the company scout from the model, once a week: careers links for employers on the sponsor lists that the
radar does not follow yet, and up to ten more employers that hire the person's target roles in the US and sponsor
work visas. Written by radar/agents.py with the API or a coding assistant. Every link is checked by radar/scout.py
before anything is shown; a made-up link finds nothing and costs one request."""

from datetime import datetime, timedelta

from radar import scout, scoutprobe, store
from tailoring import resumes

EVERY_DAYS, ASK = 7, 25  # days between suggestions; names sent for links each time
RULES = """You help one person's US job search find employers to follow. For each name under CHECK, give the link
to its jobs only if it is on one of four systems: an address on myworkdayjobs.com, job-boards.greenhouse.io or
boards.greenhouse.io, jobs.lever.co, or jobs.ashbyhq.com. An employer's own careers page does not count: give "".
Then suggest up to ten employers that are not under FOLLOWED or CHECK, hire for the target roles in the US and
sponsor work visas, each with such a link if you know one, and why in one sentence. Never make up a link: when
unsure, give "". Plain sentences, no em dashes."""
S = {"type": "string"}


def _obj(props):
    return {"type": "object", "additionalProperties": False, "properties": props, "required": list(props)}


SCHEMA = _obj(
    {
        "known": {"type": "array", "items": _obj({"name": S, "link": S})},
        "new": {"type": "array", "items": _obj({"name": S, "link": S, "why": S})},
    }
)


def due(cfg=None, every=False, today=None):
    """One batch a week (scout_every_days); with every, one now."""
    today, last = today or datetime.now(), scout.load().get("suggested", "")
    days = ((cfg or {}).get("agents") or {}).get("scout_every_days", EVERY_DAYS)
    if not every and last and last > (today - timedelta(days=days)).strftime("%Y-%m-%d"):
        return []
    return [{"key": f"leads|{today:%Y-%m-%d}", "company": "", "req_id": "", "title": "employer leads"}]


def choose(found):
    return found[0] if found else None


def packet(item):
    state = scout.gather(scout.load())
    check = [n for n, v in state["leads"].items() if v["status"] in ("new", "none") and not v["link"]][:ASK]
    cfg, names = scout.read("config.json", {}), sorted(c["name"] for c in scout.read("companies.json", []))
    roles = ", ".join(cfg.get("search_terms", []))
    return item | {"check": check, "followed": names, "roles": roles, "profile": resumes.profile_text()[:1500]}


def rules():
    return RULES


def prompt(p):
    return (
        f"TARGET ROLES: {p['roles']}\n\nPROFILE:\n{p['profile']}\n\nCHECK:\n"
        + "\n".join(p["check"])
        + "\n\nFOLLOWED:\n"
        + ", ".join(p["followed"])
        + "\n\nGive the links and the suggestions."
    )


def check(answer):
    return []


def store_answer(item, answer, by, p, problems=()):
    """Links go onto their leads, looked at again next run; suggestions become leads of their own."""
    today = datetime.now().strftime("%Y-%m-%d")
    with store.lock():
        state = scout.gather(scout.load())
        taken = scout.followed() | {n.lower() for n in state["leads"]}
        for k in answer["known"]:  # a link on a system the poll cannot read is no help: dropped
            lead = state["leads"].get(k["name"])
            if lead and scoutprobe.readable(k["link"].strip()) and lead["status"] in ("new", "none"):
                lead |= {"link": k["link"].strip(), "status": "new"}
        for n in answer["new"][:10]:
            if n["name"].strip() and n["name"].lower() not in taken:
                taken.add(n["name"].lower())
                link = n["link"].strip() if scoutprobe.readable(n["link"].strip()) else ""
                lead = {"source": "suggested", "link": link, "why": n["why"], "status": "new"}
                state["leads"][n["name"].strip()] = lead | {"added": today}
        store.write_json(scout.STATE, state | {"suggested": today, "suggested_by": by})
