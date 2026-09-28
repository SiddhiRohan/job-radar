"""Employers on Greenhouse, Lever or Ashby. Their public job-board APIs list every open posting with its description in
one response, so a board is fetched whole, once per run, with no search terms; radar/boardparse.py reads it."""

from urllib.parse import quote

from radar import boardparse, wd

URLS = {
    "greenhouse": "https://boards-api.greenhouse.io/v1/boards/{board}/jobs?content=true",
    "lever": "https://api.lever.co/v0/postings/{board}?mode=json",
    "ashby": "https://api.ashbyhq.com/posting-api/job-board/{board}?includeCompensation=true",
}
PARSERS = {"greenhouse": boardparse.greenhouse, "lever": boardparse.lever, "ashby": boardparse.ashby}


def system(company):
    """'greenhouse', 'lever' or 'ashby' for a board employer; None for Workday (no "ats" key, or "ats": "workday")."""
    ats = (company.get("ats") or "workday").strip().lower()
    return None if ats == "workday" else ats


def fetch(company, now=None):
    """Every open posting on the employer's board. One request through wd.request_json, so the 1.5 s gap, the
    retries and the 6-hour cache are the same as for Workday."""
    ats = system(company)
    if ats not in URLS or not company.get("board"):
        raise ValueError(f"{company.get('name')}: needs ats greenhouse, lever or ashby and a board, has {ats!r}")
    data = wd.request_json(URLS[ats].format(board=quote(company["board"], safe="")))
    return PARSERS[ats](company["name"], data, now)
