"""No API key: the writing agents' work as a task file a coding assistant answers, and its answers stored once they
pass the same checks the API's get. Used by python -m radar.agents next and save, and by /radar-agents."""

import json
from pathlib import Path

from radar import agents, handscore

TASKS = Path(".cache/agent_tasks.json")
HOW = (
    "Answer each task as its agent's rules say, from the task's input alone, following that agent's schema exactly. "
    'Write one JSON object {"<task id>": answer, ...} to .cache/agent_answers.json, then run '
    "python -m radar.agents save .cache/agent_answers.json."
)


def write(names=None, who=None):
    """Put every due task, with each agent's rules and schema once, in the task file. Returns the task ids."""
    cfg, tasks, rules = agents.config(), [], {}
    for name, mod in agents.WRITERS.items():
        if names and name not in names:
            continue
        for item in agents.todo(name, cfg, who):
            rules[name] = {"rules": mod.rules(), "schema": mod.SCHEMA}
            tasks.append({"id": f"{name}:{item['key']}", "agent": name, "input": mod.prompt(mod.packet(item))})
    TASKS.parent.mkdir(parents=True, exist_ok=True)
    TASKS.write_text(json.dumps({"how": HOW, "agents": rules, "tasks": tasks}, indent=1), encoding="utf-8")
    return [t["id"] for t in tasks]


def save(answers):
    """Store each answer that passes its agent's schema and checks. Returns (stored ids, {id: problems})."""
    if not isinstance(answers, dict):
        raise ValueError('the file should hold one JSON object, {"<task id>": answer, ...}')
    cfg, stored, rejected = agents.config(), [], {}
    for tid, answer in answers.items():
        name, _, key = tid.partition(":")
        mod = agents.WRITERS.get(name)
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
