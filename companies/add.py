"""python -m companies.add "Name" <link>: add an employer to the daily search from any link to its jobs, whether a
Workday careers site or posting, or a Greenhouse, Lever or Ashby board or posting.

One request checks the link the way the daily poll reads it, then the employer goes into companies.json, verified,
with sponsorship and tier from expand.py's lists. Running it again with the same name updates the entry. The Workday
address comes only from the link given, never from a guess: Workday answers alike for real and made-up tenants."""

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

from companies import board, expand
from radar import wd

SITE_URL = re.compile(r"https?://([\w-]+)\.(wd\d+)\.myworkdayjobs\.com/(?:[a-z]{2}-[A-Z]{2}/)?([^/?#]+)", re.I)


def workday_from_url(url):
    """(tenant, shard, site) from a Workday careers site or posting URL, or None for any other link."""
    m = SITE_URL.match((url or "").strip())
    return (m.group(1).lower(), m.group(2).lower(), m.group(3)) if m else None


def add_workday(name, tenant, shard, site, roles, path="companies.json"):
    """Add or update a Workday employer, verified now; unknown sponsorship starts in tier 2, as board employers do."""
    companies = json.loads(Path(path).read_text(encoding="utf-8"))
    c = next((c for c in companies if c["name"] == name), None)
    if c and c.get("ats") not in (None, "workday"):
        raise ValueError(f"{name} is a {c['ats']} employer in {path}; remove its ats and board first")
    if c is None:
        c = {"name": name}
        companies.append(c)
    s, source = expand.sponsorship(name, c.get("sponsors_h1b"))
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    c.update(tenant=tenant, shard=shard, site=site, verified=True, verified_at=now, open_roles=roles, sponsors_h1b=s)
    c.update(sponsorship_source=source, tier=expand.tier(name, s) if s is not None else 2)
    companies.sort(key=lambda c: (c["tier"], c["name"]))
    Path(path).write_text(json.dumps(companies, indent=2) + "\n", encoding="utf-8")
    return c


def main(argv):
    if len(argv) != 2:
        print('usage: python -m companies.add "Name" <link to its careers site, job board or one posting>')
        return 2
    name, url = argv
    found, site = board.board_from_url(url), workday_from_url(url)
    if not (found or site):
        print("not a link the radar reads: use a Workday site or posting, or a Greenhouse, Lever or Ashby board")
        return 1
    try:
        if found:
            roles = board.check(found["ats"], found["board"])
            c = board.add(name, found["ats"], found["board"], roles)
            where = f"{c['ats']} board {c['board']!r}"
        else:
            roles = wd.count(*site)
            c = add_workday(name, *site, roles)
            where = f"Workday site {site[0]}.{site[1]}/{site[2]}"
    except (requests.RequestException, ValueError) as e:
        print(f"{name} not added: {str(e)[:150]}")
        return 1
    print(f"{name}: {where}, {roles} open postings, tier {c['tier']}; the next run includes it")
    if not roles:
        print("  no open postings: check this is the employer's current careers site")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main(sys.argv[1:]))
