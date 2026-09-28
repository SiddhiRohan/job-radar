"""Employers on Greenhouse, Lever or Ashby. python -m companies.board "Name" URL reads the board from a careers, board
or posting URL, checks it with one request (the one the poll makes), and adds or updates the employer in
companies.json with sponsorship and tier from expand.py's lists. Workday URLs keep their own path (companies.ledger)."""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

import requests

from companies import expand
from radar import boards

HOSTS = {
    "boards.greenhouse.io": "greenhouse",
    "job-boards.greenhouse.io": "greenhouse",
    "boards-api.greenhouse.io": "greenhouse",
    "jobs.lever.co": "lever",
    "api.lever.co": "lever",
    "jobs.ashbyhq.com": "ashby",
    "api.ashbyhq.com": "ashby",
}
NOT_BOARD = {"v0", "v1", "boards", "postings", "posting-api", "job-board", "embed", "job_board", "job_app"}


def board_from_url(url):
    """{"ats", "board"} from a URL on one of the three systems, for example job-boards.greenhouse.io/<board>/jobs/1,
    jobs.lever.co/<board>/<id> or jobs.ashbyhq.com/<board>; None for any other URL, Workday's included."""
    url = (url or "").strip()
    u = urlparse(url if "://" in url else "https://" + url)
    ats = HOSTS.get(u.hostname or "")
    embed = parse_qs(u.query).get("for")  # boards.greenhouse.io/embed/job_board?for=<board>
    parts = [unquote(p) for p in u.path.split("/") if p and p not in NOT_BOARD]
    board = embed[0] if embed else (parts[0] if parts else None)
    return {"ats": ats, "board": board} if ats and board else None


def check(ats, board):
    """Open postings on the board. Raises when the board is missing or answers with anything but postings."""
    return len(boards.fetch({"name": board, "ats": ats, "board": board}))


def add(name, ats, board, roles, path="companies.json"):
    """Add or update a board employer, verified now. Sponsorship comes from expand.py's lists; tier follows it, and an
    employer whose sponsorship is unknown starts in tier 2 until its filings are checked."""
    companies = json.loads(Path(path).read_text(encoding="utf-8"))
    c = next((c for c in companies if c["name"] == name), None)
    if c and c.get("tenant"):
        raise ValueError(f"{name} is a Workday employer in {path}; remove its tenant, shard and site first")
    if c is None:
        c = {"name": name}
        companies.append(c)
    s, source = expand.sponsorship(name, c.get("sponsors_h1b"))
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    c.update(ats=ats, board=board, verified=True, verified_at=now, open_roles=roles, sponsors_h1b=s)
    c.update(sponsorship_source=source, tier=expand.tier(name, s) if s is not None else 2)
    companies.sort(key=lambda c: (c["tier"], c["name"]))
    Path(path).write_text(json.dumps(companies, indent=2) + "\n", encoding="utf-8")
    return c


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) != 3:
        sys.exit('usage: python -m companies.board "Name" <careers, board or posting URL>')
    name, url = sys.argv[1:]
    found = board_from_url(url)
    if not found:
        sys.exit(f"not a Greenhouse, Lever or Ashby URL: {url}")
    try:
        roles = check(found["ats"], found["board"])
        c = add(name, found["ats"], found["board"], roles)
    except (requests.RequestException, ValueError) as e:
        sys.exit(f"{name}: {found['ats']} board {found['board']!r} not added: {str(e)[:150]}")
    print(f"{name}: {c['ats']} board {c['board']!r}, {roles} open postings, tier {c['tier']}")
    if not roles:
        print("  no open postings: check this is the employer's current board")


if __name__ == "__main__":
    main()
