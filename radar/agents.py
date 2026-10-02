"""python -m radar.agents: the agents that work from the radar's own records after each run.

  run [prep|followups] [--for COMPANY [REQ_ID]]   write what is due, with the Anthropic API
  next [prep|followups] [--for COMPANY [REQ_ID]]  no API key: put the tasks in .cache/agent_tasks.json for a
                                                   coding assistant to answer
  save FILE                                        store the assistant's answers once they pass the checks
  show prep|followups [COMPANY]                    print what they wrote

Two agents write for the person: interview prep (radar/prep.py) and follow-up drafts (radar/followup.py). Two more
read the records and need no model: skill gaps (radar/gaps.py) and the sponsor map (radar/sponsormap.py). Settings
live under "agents" in config.json; docs/CONFIG.md explains them."""

import json
import sys
from pathlib import Path

import requests

from radar import agentview, followup, handscore, llm, prep, score

WRITERS = {"prep": prep, "followups": followup}
PER_RUN = 5
TASKS = Path(".cache/agent_tasks.json")
HOW = (
    "Answer each task as its agent's rules say, from the task's input alone, following that agent's schema exactly. "
    'Write one JSON object {"<task id>": answer, ...} to a file, then run python -m radar.agents save <file>.'
)


def has_key():
    return bool(score.load_api_key(required=False))


def config():
    try:
        return json.loads(Path("config.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def todo(name, cfg, who=None):
    """One writer's work: what is due, or with who=(company, req_id or None) that employer's applications, the ones
    at a screen or interview first. An agent turned off in config.json has nothing due but still answers by name."""
    mod = WRITERS[name]
    if who is None:
        return mod.due(cfg) if (cfg.get("agents") or {}).get(name, True) else []
    company, req_id = who[0].lower(), who[1]
    every = mod.due(cfg, every=True)
    found = [i for i in every if i["company"].lower() == company] or [
        i for i in every if company in i["company"].lower()
    ]
    found = [i for i in found if not req_id or i["req_id"] == req_id]
    return sorted(found, key=lambda i: i.get("stage") not in prep.STAGES)


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
    out = {}
    for name, mod in WRITERS.items():
        if names and name not in names:
            continue
        items, r = todo(name, cfg, who), {"made": [], "waiting": 0, "errors": []}
        out[name] = r
        if not key:
            r["waiting"] = len(items)
            continue
        for item in items[:cap]:
            try:
                write(mod, item, complete)
                r["made"].append(item["key"])
            except (OSError, RuntimeError, ValueError, KeyError, requests.RequestException) as e:
                r["errors"].append(f"{item['key']}: {str(e)[:160]}")
        r["waiting"] = max(0, len(items) - cap)
    return out


def next_tasks(names=None, who=None):
    """Write every due task, with each agent's rules and schema once, for a coding assistant. Returns the task ids."""
    cfg, tasks, agents = config(), [], {}
    for name, mod in WRITERS.items():
        if names and name not in names:
            continue
        for item in todo(name, cfg, who):
            agents[name] = {"rules": mod.rules(), "schema": mod.SCHEMA}
            tasks.append({"id": f"{name}:{item['key']}", "agent": name, "input": mod.prompt(mod.packet(item))})
    TASKS.parent.mkdir(parents=True, exist_ok=True)
    TASKS.write_text(json.dumps({"how": HOW, "agents": agents, "tasks": tasks}, indent=1), encoding="utf-8")
    return [t["id"] for t in tasks]


def save_answers(answers):
    """Store each answer that passes its agent's schema and checks. Returns (stored ids, {id: problems})."""
    if not isinstance(answers, dict):
        raise ValueError('the file should hold one JSON object, {"<task id>": answer, ...}')
    cfg, stored, rejected = config(), [], {}
    for tid, answer in answers.items():
        name, _, key = tid.partition(":")
        mod = WRITERS.get(name)
        item = next((i for i in mod.due(cfg, every=True) if i["key"] == key), None) if mod else None
        if item is None:
            rejected[tid] = ["no such task: ids look like prep:<company>|<req_id>, as in the task file"]
            continue
        found = handscore.problems(answer, mod.SCHEMA, "answer") or mod.check(answer)
        if found:
            rejected[tid] = found
            continue
        mod.store_answer(item, answer, "assistant", mod.packet(item))
        stored.append(tid)
    return stored, rejected


def main(argv):
    cmd, rest = (argv[0], list(argv[1:])) if argv else ("run", [])
    names = [rest.pop(0)] if rest and rest[0] in WRITERS else None
    who = (rest[1], rest[2] if len(rest) > 2 else None) if rest[:1] == ["--for"] and len(rest) > 1 else None
    if cmd == "run":
        for name, r in run(names, who).items():
            print(
                f"{name}: wrote {len(r['made'])}, {r['waiting']} waiting" + "".join(f"\n  ! {e}" for e in r["errors"])
            )
        if not has_key():
            print("no API key: python -m radar.agents next writes the waiting tasks for your coding assistant")
        return 0
    if cmd == "next":
        ids = next_tasks(names, who)
        print(f"tasks: {len(ids)}, in {TASKS}" if ids else "nothing is waiting for an agent")
        return 0
    if cmd == "save" and rest:
        stored, rejected = save_answers(json.loads(Path(rest[0]).read_text(encoding="utf-8")))
        print(
            f"stored: {len(stored)}" + "".join(f"\n  not stored, {t}: " + "; ".join(p[:4]) for t, p in rejected.items())
        )
        return 1 if rejected else 0
    if cmd == "show" and names:
        print(agentview.text(names[0], rest[0] if rest else None))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main(sys.argv[1:]))
