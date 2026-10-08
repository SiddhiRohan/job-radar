"""Employers on Greenhouse, Lever or Ashby. Their public job-board APIs list every open posting with its description in
one response, so a board is fetched whole, once per run, with no search terms; radar/boardparse.py reads it, and
screen() applies the rules poll.py applies to Workday search results."""

from urllib.parse import quote

from radar import boardparse, dropped, filters, wd

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


def screen(cfg, company, jobs, max_days, found, removed, log=None):
    """The Workday path's rules on a whole board. A posting counts under the first term whose date window it is in
    and whose title rule it passes; then the seniority, domain and US rules. Entry terms stand in for Workday's
    relevance search, which a board lacks, so they count only for titles with entry wording. Returns how many
    postings fell inside a window. Each drop goes to log, when given, for the filter auditor."""
    log = [] if log is None else log
    role_terms = cfg["search_terms"] + list(company.get("extra_terms") or [])
    entry_terms = cfg.get("entry_terms", []) if company.get("tier", 1) <= 2 else []
    wide = max(max_days, cfg.get("entry_max_days_ago", max_days))
    must_match = cfg.get("title_must_match_term", True)
    fresh = 0
    for j in jobs:
        key, days, title = f"{company['name']}|{j['req_id']}", j["posted_days_ago"], j["title"]
        terms = list(role_terms) if days <= max_days else []
        if days <= wide and filters.is_entry_title(title):
            terms += entry_terms
        if key in found or not terms:
            continue
        fresh += 1
        terms.sort(key=lambda t: t.lower() not in title.lower())  # store the term the title names, when one does
        term = next((t for t in terms if not must_match or filters.title_matches_term(title, t, cfg)), None)
        if term is None:
            log.append(dropped.item(company["name"], j, "off_target"))
            continue
        reason = filters.title_exclusion(title, cfg)
        if reason:
            removed[reason].add(key)
            log.append(dropped.item(company["name"], j, reason))
        elif cfg["us_only"] and j["detail"]["non_us"]:
            removed["non_us"].add(key)
            log.append(dropped.item(company["name"], j, "non_us"))
        else:
            j["search_term"] = term
            found[key] = j
    return fresh


def poll(cfg, company, max_days, found, removed, errors, now=None, log=None):
    """Fetch one board and screen it into found and removed. A failure is recorded in errors, never raised."""
    ats = system(company)
    try:
        jobs = fetch(company, now)
    except Exception as e:  # keep polling the other companies
        errors[company["name"]] = f"{ats} board: {str(e)[:150]}"
        print(f"  ! {company['name']} / {ats} board: {str(e)[:90]}", flush=True)
        return
    fresh = screen(cfg, company, jobs, max_days, found, removed, log)
    print(f"  {company['name']:<12} {ats + ' board':<22} {len(jobs):>4} results, {fresh:>3} recent", flush=True)


def find(company, req_id, fetch_board=None):
    """The open posting with this id, or None once the board no longer lists it. Raises when the board cannot be
    read or lists nothing at all: an empty answer says more about the board than about one posting."""
    postings = (fetch_board or fetch)(company)
    if not postings:
        raise ValueError("the board listed no postings")
    return next((p for p in postings if p["req_id"] == str(req_id)), None)
