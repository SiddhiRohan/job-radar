"""The terminal side of python -m radar.agents. radar/agents.py runs the agents; this reads the command line.

  run [AGENT] [--for COMPANY [REQ_ID]]    write what is due, or one application's, with the Anthropic API
  next [AGENT] [--for COMPANY [REQ_ID]]   no API key: put the tasks in .cache/agent_tasks.json for a coding
                                          assistant to answer (radar/agenttasks.py)
  save FILE                               store the assistant's answers once they pass the checks
  show AGENT [COMPANY]                    print what an agent wrote
  debrief COMPANY [REQ_ID] < account.txt  keep how an interview went, then write its debrief
  audit [apply N]                         write the filter audit now, or make its suggested change N

AGENT is prep, followups, debrief or audit."""

import json
import sys
from pathlib import Path

from radar import agents, agenttasks, agentview, audit, debrief


def pick(name, company, req_id=None):
    """The one application an agent would choose at an employer, or None."""
    found = agents.matching(agents.WRITERS[name].due({}, every=True), company, req_id)
    return agents.WRITERS[name].choose(found)


def report(results):
    for name, r in results.items():
        print(f"{name}: wrote {len(r['made'])}, {r['waiting']} waiting" + "".join(f"\n  ! {e}" for e in r["errors"]))
    if not agents.has_key():
        print("no API key: python -m radar.agents next writes the waiting tasks for your coding assistant")


def keep_account(args, account):
    """debrief COMPANY [REQ_ID]: store the account for the employer's application, then write the debrief."""
    app = pick("prep", args[0], args[1] if len(args) > 1 else None)  # prep sees every application
    if app is None:
        print(f"no application at {args[0]} on the Applied list")
        return 1
    if not debrief.add(app["company"], app["req_id"], account):
        print("say how it went: the account was empty")
        return 1
    print(f"kept your account of {app['title']} at {app['company']}")
    report(agents.run(["debrief"], (app["company"], app["req_id"])))
    return 0


def main(argv, stdin=sys.stdin):
    cmd, rest = (argv[0], list(argv[1:])) if argv else ("run", [])
    names = [rest.pop(0)] if rest and rest[0] in agents.WRITERS else None
    who = (rest[1], rest[2] if len(rest) > 2 else None) if rest[:1] == ["--for"] and len(rest) > 1 else None
    try:
        if cmd == "run":
            report(agents.run(names, who))
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
        if cmd == "debrief" and rest:
            return keep_account(rest, stdin.read())
        if cmd == "audit" and rest[:1] == ["apply"] and len(rest) > 1:
            print(audit.apply(int(rest[1]) - 1))  # numbered from 1, as the audit lists them
            return 0
        if cmd == "audit":
            report(agents.run(["audit"], ("", None)))
            print(agentview.text("audit"))
            return 0
    except (OSError, ValueError) as e:
        print(f"could not {cmd}: {e}")
        return 1
    print(__doc__)
    return 2
