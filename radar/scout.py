"""python -m radar.scout [follow NAME | skip NAME | show]: the company scout. It finds employers worth adding to the
daily search and checks each with the requests the poll would make, a few a morning at the usual 1.5 s gap.

Leads: employers the person applied to or evaluated without following them, the H-1B sponsor lists and earlier
searches in companies/, and the model's weekly suggestions (radar/leads.py). A lead with a careers link is checked at
that link; one without is looked for on Greenhouse, Lever and Ashby under its name. Workday addresses are never
guessed, since Workday answers alike for real and made-up tenants. Found employers wait on the Agents view until the
person follows or skips them; nothing joins companies.json without that. State in .cache/ui/scout.json."""

import json
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

import requests

from companies import add, expand  # their lists load from the repo root, where every entry point runs
from radar import applications, scoutprobe, store

STATE = Path(".cache/ui/scout.json")
PER_RUN = 5
FIRST = {
    "you applied there": 0,
    "you evaluated a posting": 1,
    "suggested": 2,
    "top H-1B sponsor": 3,
    "earlier search": 4,
}


def load():
    try:
        return json.loads(STATE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"leads": {}}


def read(path, empty):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return empty


def followed():
    return {c["name"].lower() for c in read("companies.json", [])}


def gather(state, jobs=None):
    """Add the leads not known yet, best first: where they applied or looked, then the lists in companies/."""
    have, today = followed() | {n.lower() for n in state["leads"]}, datetime.now().strftime("%Y-%m-%d")

    def lead(name, source, link=""):
        if name and name.lower() not in have:
            have.add(name.lower())
            state["leads"][name] = {"source": source, "link": link, "status": "new", "added": today}

    links = {j["company"]: j.get("url", "") for j in (store.load() if jobs is None else jobs)}
    for a in applications.rows():
        lead(a["company"], "you applied there", links.get(a["company"], ""))
    for name, link in links.items():
        lead(name, "you evaluated a posting", link)
    for name in sorted(expand.H1B_TOP - expand.NO_SPONSOR):
        lead(name, "top H-1B sponsor")
    for path in ("companies/recheck_later.json", "companies/not_on_workday.json"):
        for name in read(path, {}):
            lead(name, "earlier search")
    return state


def check(cfg, limit=None):
    """Look up to `limit` new leads, those with a link first. Returns the names found."""
    with store.lock():
        state = gather(load())
        store.write_json(STATE, state)
    new = [n for n, v in state["leads"].items() if v["status"] == "new"]
    new.sort(
        key=lambda n: (not scoutprobe.readable(state["leads"][n]["link"]), FIRST.get(state["leads"][n]["source"], 9), n)
    )
    found = []
    for name in new[: limit or (cfg.get("agents") or {}).get("scout_per_run", PER_RUN)]:
        lead, today = state["leads"][name], datetime.now().strftime("%Y-%m-%d")
        try:
            linked = scoutprobe.readable(lead["link"])  # any other careers page: look on the boards by name
            hit = scoutprobe.at_link(lead["link"], cfg) if linked else scoutprobe.on_boards(name, cfg)
        except (requests.RequestException, ValueError, KeyError) as e:
            hit, lead["note"] = None, str(e)[:120]
        lead |= {"checked": today, "status": "found" if hit else "none"}
        if hit:
            lead |= dict(zip(("ats", "url", "roles", "matching"), hit))
            found.append(name)
        with store.lock():
            latest = load()
            latest["leads"][name] = lead
            store.write_json(STATE, latest | {"checked": today})
    return found


def decide(name, how):
    """Follow a found employer (companies.add checks it once more and adds it) or skip it. {"ok", "message"}."""
    lead = load()["leads"].get(name)
    if not lead or lead["status"] != "found":
        return {"ok": False, "message": f"{name} is not an employer the scout found"}
    result = add.add(name, lead["url"]) if how == "follow" else {"ok": True, "message": f"{name} skipped"}
    if result["ok"]:
        with store.lock():
            state = load()
            state["leads"][name]["status"] = "followed" if how == "follow" else "skipped"
            store.write_json(STATE, state)
    return result


def report():
    """Found employers, those matching the most titles first, with their H-1B record; and how far the scout got."""
    state = load()
    found = [dict(v, name=k) for k, v in state["leads"].items() if v["status"] == "found"]
    for f in found:
        f["sponsors"], f["sponsor_source"] = expand.sponsorship(f["name"], None)
    found.sort(key=lambda f: (-f["matching"], -f["roles"], f["name"]))
    counts = Counter(v["status"] for v in state["leads"].values())
    return {
        "found": found,
        "counts": dict(counts),
        "checked": state.get("checked"),
        "suggested": state.get("suggested"),
    }


def summary(r, limit=8):
    """Plain lines: each found employer with what was found, then how far the scout got."""
    lines = [
        f"{f['name']}: {f['ats']}, {f['roles']} open, {f['matching']} matching your titles, {f['sponsor_source']}; "
        f"{f.get('why') or f['source']}. {f['url']}"
        for f in r["found"][:limit]
    ]
    left = r["counts"].get("new", 0)
    tail = [f"{left} leads wait to be checked, a few each morning."] if left else []
    return (lines or ["No employer found yet."]) + tail


def main(argv):
    if argv[:1] in (["follow"], ["skip"]) and len(argv) == 2:
        print(decide(argv[1], argv[0])["message"])
        return 0
    if argv[:1] != ["show"]:
        cfg = json.loads(Path("config.json").read_text(encoding="utf-8"))
        print("scout: found " + (", ".join(check(cfg)) or "nothing new this time"))
    r = report()
    for f in r["found"]:
        print(f"  {f['name']}: {f['ats']}, {f['roles']} open, {f['matching']} matching your titles | {f['url']}")
    print(f'leads: {r["counts"]}; follow one with python -m radar.scout follow "Name"')
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main(sys.argv[1:]))
