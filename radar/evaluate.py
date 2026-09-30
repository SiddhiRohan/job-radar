"""python -m radar.evaluate <job url> [--json]: fetch one posting, score it, store it, and print the verdict.
   python -m radar.evaluate <company> <req_id> [--json]: print the verdict of a posting already stored.

The link can be a Workday posting or one on Greenhouse, Lever or Ashby. The web app's Tailor box and a coding
assistant both use this, so a posting found anywhere is judged the same way as the ones the daily run finds. A
posting already stored is returned as it is, without a new request."""

import json
import sys
from datetime import datetime
from urllib.parse import parse_qs, urlparse

from companies import board as boardurl
from radar import boards, digest, poll, salary, score, wd


def store_new(j, company, detail=None):
    """Enrich and score a posting the radar has not seen, append it to jobs.jsonl, and return it."""
    j |= {"search_term": "pasted", "first_seen": datetime.now().astimezone().isoformat(timespec="seconds")}
    poll.enrich(j, company, json.load(open("config.json", encoding="utf-8")), detail)
    j["verdict"] = score.rule_verdict(j) or score.ask_claude(score.load_api_key(), score.system_blocks(), j)[0]
    with open("jobs.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(j) + "\n")
    return j


def stored(company, req_id):
    return next((j for j in digest.load_jsonl("jobs.jsonl") if j["req_id"] == req_id and j["company"] == company), None)


def ingest_board(url, where):
    """A posting on a Greenhouse, Lever or Ashby board: read the board once and pick the posting the link names."""
    known = json.load(open("companies.json", encoding="utf-8"))
    c = next((k for k in known if boards.system(k) == where["ats"] and k.get("board") == where["board"]), None)
    c = c or {"name": where["board"].replace("-", " ").title(), **where, "sponsors_h1b": None}
    u = urlparse(url)
    ids = {p for p in u.path.split("/") if p} | set(parse_qs(u.query).get("gh_jid", []))
    p = next((x for x in boards.fetch(c) if x["req_id"] in ids), None)
    if p is None:
        raise ValueError("that posting is no longer on the board, or the link is to the board rather than a posting")
    detail = p.pop("detail")
    return stored(c["name"], p["req_id"]) or store_new(p, c, detail)


def ingest_url(url):
    """Parse a pasted job URL, fetch and score it if jobs.jsonl does not have it, return the record."""
    where = boardurl.board_from_url(url)
    if where:
        return ingest_board(url, where)
    parsed = wd.parse_job_url(url)
    if not parsed:
        raise ValueError(
            "that is not a job link the radar reads: use a Workday posting, or one on Greenhouse, Lever or Ashby"
        )
    tenant, shard, site, ext, req_id = parsed
    comps = {c["tenant"]: c for c in json.load(open("companies.json", encoding="utf-8")) if c.get("tenant")}
    c = comps.get(tenant) or {"name": tenant, "tenant": tenant, "shard": shard, "site": site, "sponsors_h1b": None}
    known = stored(c["name"], req_id)
    if known:
        return known
    d = wd.fetch_detail(tenant, shard, f"/wday/cxs/{tenant}/{site}{ext}")
    j = {
        "company": c["name"],
        "title": d.get("title") or req_id,
        "location": d["location"] or "",
        "posted_on": "pasted",
        "posted_days_ago": 0,
        "req_id": req_id,
        "url": url,
        "detail_path": f"/wday/cxs/{tenant}/{site}{ext}",
    }
    return store_new(j, c, d)


def summary(j):
    """Plain lines a person or an assistant can read."""
    v = j.get("verdict") or {}
    pay = salary.extract(j.get("description", ""))
    lines = [
        f"{j['company']} | {j['title']} | {j.get('detail_location') or j.get('location', '')} | {j['req_id']}",
        f"fit: entry {v.get('score_entry', '-')} / experienced {v.get('score_experienced', '-')}"
        + (f", use the {v['recommended_resume']} resume" if v.get("recommended_resume") else ""),
        f"sponsorship: {j.get('sponsorship') or 'unknown'}"
        + (f' ("{j["sponsorship_evidence"]}")' if j.get("sponsorship_evidence") else ""),
        f"years asked: {j['years_required'] if j.get('years_required') is not None else 'not stated'}"
        f" | pay: {pay['text'] if pay else 'not listed'}",
    ]
    if v.get("hard_requirements_missing"):
        lines.append("missing: " + ", ".join(v["hard_requirements_missing"]))
    if v.get("why") or v.get("reason"):
        lines.append("why: " + (v.get("why") or v.get("reason")))
    lines.append(j.get("url", ""))
    return lines


def find(company, req_id):
    """A stored posting by company and requisition id, case-insensitive on the company, or None."""
    for j in digest.load_jsonl("jobs.jsonl"):
        if j["req_id"] == req_id and j["company"].lower() == company.lower():
            return j
    return None


def main(argv):
    args = [a for a in argv if not a.startswith("--")]
    if not args:
        print("\n".join(__doc__.splitlines()[:2]))
        return 2
    if len(args) == 2 and not args[0].startswith("http"):
        j = find(*args)
        if not j:
            print(f"no stored posting for {args[0]} {args[1]}; paste its link instead")
            return 1
    else:
        try:
            j = ingest_url(args[0])
        except (ValueError, RuntimeError) as e:
            print(f"could not evaluate: {e}")
            return 1
    print(json.dumps(j, indent=1) if "--json" in argv else "\n".join(summary(j)))
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main(sys.argv[1:]))
