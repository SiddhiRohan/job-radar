"""python -m radar.agents: the agents that work from the radar's own records after each run.

  run [prep|followups] [--for COMPANY [REQ_ID]]   write what is due, or one application's, with the Anthropic API
  next [prep|followups] [--for COMPANY [REQ_ID]]  no API key: put the tasks in .cache/agent_tasks.json for a
                                                   coding assistant to answer (radar/agenttasks.py)
  save FILE                                        store the assistant's answers once they pass the checks
  show prep|followups [COMPANY]                    print what they wrote

Two agents write for the person: interview prep (radar/prep.py) and follow-up drafts (radar/followup.py). Two more
read the records and need no model: skill gaps (radar/gaps.py) and the sponsor map (radar/sponsormap.py). Settings
live under "agents" in config.json; docs/CONFIG.md explains them."""

import json
import sys
import threading
from pathlib import Path

import requests

from radar import followup, handscore, llm, prep, runlock, score

WRITERS = {"prep": prep, "followups": followup}
PER_RUN = 5
BUSY = threading.Lock()  # the web app and the chat share one process: one writing run at a time


def has_key():
    return bool(score.load_api_key(required=False))


def config():
    try:
        return json.loads(Path("config.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def matching(items, company, req_id=None):
    """One employer's items: its exact name in any case, else the only employer whose name starts with what was
    typed. "GE" never reaches Target or Geico."""
    typed = company.strip().lower()
    found = [i for i in items if i["company"].lower() == typed]
    if not found:
        starts = {i["company"] for i in items if i["company"].lower().startswith(typed)}
        found = [i for i in items if i["company"] in starts] if len(starts) == 1 else []
    return [i for i in found if not req_id or i["req_id"] == req_id]


def todo(name, cfg, who=None):
    """One writer's work: what is due, or with who=(company, req_id or None) the one application its agent would
    choose there. An agent turned off in config.json has nothing due but still answers for one application."""
    mod = WRITERS[name]
    if who is None:
        return mod.due(cfg) if (cfg.get("agents") or {}).get(name, True) else []
    one = mod.choose(matching(mod.due(cfg, every=True), *who))
    return [one] if one else []


def waiting(cfg=None):
    """How many applications each writer has due, as the next run would see them."""
    cfg = config() if cfg is None else cfg
    return {name: len(todo(name, cfg)) for name in WRITERS}


def refuse():
    """Why the web app should not start a writing run now, or "" when it may."""
    if not has_key():
        return "No API key: add one on Setup, or run /radar-agents in a coding assistant."
    if runlock.held():
        return "The morning run is going; its agents step writes these when it gets there."
    return ""


def write(mod, item, complete):
    """Ask once, and once more with the problems named when the answer misses a length or count; a second miss is
    kept with the problems in its notes, since a long draft is still worth trimming by hand."""
    p = mod.packet(item)
    user = mod.prompt(p)
    for attempt in (1, 2):
        answer, model = complete(mod.rules(), user, mod.SCHEMA, max_tokens=4096)
        if problems := handscore.problems(answer, mod.SCHEMA, "answer"):
            raise ValueError("; ".join(problems[:3]))
        found = mod.check(answer)
        if not found or attempt == 2:
            return mod.store_answer(item, answer, model, p, found)
        user += "\n\nYour last answer had these problems, fix them: " + "; ".join(found)


def run(names=None, who=None, complete=None, key=None):
    """{agent: {"made": [keys], "waiting": n, "errors": [...]}}. Without an API key nothing is written and every
    due item waits, for a key or for `next` and `save`."""
    cfg, complete = config(), complete or llm.complete
    key = score.load_api_key(required=False) if key is None else key
    cap = (cfg.get("agents") or {}).get("per_run", PER_RUN)
    names = [n for n in WRITERS if not names or n in names]
    if not BUSY.acquire(blocking=False):
        return {
            n: {"made": [], "waiting": 0, "errors": ["the agents are already writing; try again shortly"]}
            for n in names
        }
    try:
        out = {}
        for name in names:
            items, r = todo(name, cfg, who), {"made": [], "waiting": 0, "errors": []}
            out[name] = r
            if not key:
                r["waiting"] = len(items)
                continue
            for item in items[:cap]:
                try:
                    write(WRITERS[name], item, complete)
                    r["made"].append(item["key"])
                except (OSError, RuntimeError, ValueError, KeyError, requests.RequestException) as e:
                    r["errors"].append(f"{item['key']}: {str(e)[:160]}")
            r["waiting"] = max(0, len(items) - cap)
        return out
    finally:
        BUSY.release()


def main(argv):
    from radar import agenttasks, agentview  # both import this module

    cmd, rest = (argv[0], list(argv[1:])) if argv else ("run", [])
    names = [rest.pop(0)] if rest and rest[0] in WRITERS else None
    who = (rest[1], rest[2] if len(rest) > 2 else None) if rest[:1] == ["--for"] and len(rest) > 1 else None
    try:
        if cmd == "run":
            for name, r in run(names, who).items():
                print(
                    f"{name}: wrote {len(r['made'])}, {r['waiting']} waiting"
                    + "".join(f"\n  ! {e}" for e in r["errors"])
                )
            if not has_key():
                print("no API key: python -m radar.agents next writes the waiting tasks for your coding assistant")
            return 0
        if cmd == "next":
            ids = agenttasks.write(names, who)
            print(f"tasks: {len(ids)}, in {agenttasks.TASKS}" if ids else "nothing is waiting for an agent")
            return 0
        if cmd == "save" and rest:
            stored, rejected = agenttasks.save(json.loads(Path(rest[0]).read_text(encoding="utf-8")))
            print(
                f"stored: {len(stored)}"
                + "".join(f"\n  not stored, {t}: " + "; ".join(p[:4]) for t, p in rejected.items())
            )
            return 1 if rejected else 0
        if cmd == "show" and names:
            print(agentview.text(names[0], rest[0] if rest else None))
            return 0
    except (OSError, ValueError) as e:
        print(f"could not {cmd}: {e}")
        return 1
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main(sys.argv[1:]))
