# Phase 1 kickoff: personal Workday job radar

Paste everything below the line into Claude Code, from inside a fresh folder
that contains `companies.json` and your resume (`resume.pdf` or `resume.md`).

Work through it step by step. Do not skip to step 5 until steps 1 to 4 are
green. Ask me if a Workday response doesn't match the field names described,
then inspect the raw JSON and adapt.

---

I'm building a personal job radar that pulls postings directly from company
Workday career sites, filters to the last 24 hours, scores them against my
resume, and gives me a daily digest. Python 3.11+, only `requests` plus the
standard library unless you have a strong reason. Keep the code plain and
readable, no frameworks, no classes unless they earn it. Commit after each
step with a one-line message.

## Step 1: Workday client (`wd.py`)

Every Workday career site exposes the same JSON endpoint:

  POST https://{tenant}.{shard}.myworkdayjobs.com/wday/cxs/{tenant}/{site}/jobs
  headers: Content-Type: application/json, Accept: application/json,
           plus a normal browser User-Agent
  body:    {"appliedFacets": {}, "limit": 20, "offset": 0, "searchText": "..."}

The response has `total` and `jobPostings`. Each posting typically has
`title`, `externalPath`, `locationsText`, `postedOn` (a string like
"Posted Today", "Posted Yesterday", "Posted 3 Days Ago", "Posted 30+ Days Ago"),
and `bulletFields` (the req ID is usually in there). The job URL is
`https://{tenant}.{shard}.myworkdayjobs.com/en-US/{site}` + `externalPath`.
Job detail is at the same base with `/wday/cxs/{tenant}/{site}` + externalPath,
and the description lives under `jobPostingInfo.jobDescription` (HTML).

Write:
- `search(tenant, shard, site, text, max_pages=10)` that pages by offset,
  returns a list of normalized dicts: company, title, location, posted_on,
  posted_days_ago (int, parse the string; treat "30+" as 30), req_id, url,
  detail_path.
- `fetch_description(...)` that returns plain text from the HTML.
- A 1.5 second sleep between requests and retry with backoff on 429/5xx.
- Cache raw responses in `.cache/` keyed by URL+body hash for 6 hours so
  reruns today don't re-hit Workday.

## Step 2: verify the seed list (`verify.py`)

Load `companies.json`. For each entry with tenant/shard/site filled in, call
the endpoint with an empty searchText and record `total`. Set
`verified: true` and add `open_roles` and `verified_at`. If it 404s or the
JSON is wrong, try the tenant root and follow the redirect to find the real
site slug, then retry once. Print a table. Write the updated file back.

For entries with `"todo": "resolve slug"`, web search
"<company> myworkdayjobs" and extract tenant/shard/site from the first
myworkdayjobs.com URL you find, then verify the same way. If you can't
resolve one, leave it and tell me.

## Step 3: the poller (`poll.py`)

Config in `config.json`:

  {
    "search_terms": ["data scientist", "data engineer", "machine learning",
                     "New College Grad 2026", "AI engineer", "applied scientist"],
    "max_days_ago": 1,
    "us_only": true,
    "exclude_title_words": ["senior", "principal", "staff", "director",
                            "manager", "intern", "phd"],
    "include_title_words": []
  }

For every verified company and every search term, call `search`, merge,
dedupe by (company, req_id). Keep only postings with
posted_days_ago <= max_days_ago. Apply the title word filters
(case-insensitive). If us_only, drop locations that clearly aren't US
(look for country names or well-known non-US cities; when unsure, keep it).

Maintain `seen.json` (a set of company+req_id). Anything not in it is "new".
Append new ones to `jobs.jsonl` with a `first_seen` timestamp, then update
`seen.json`.

Print a table of new postings sorted by company then title.

## Step 4: fit scoring (`score.py`)

Read my resume (`resume.pdf` or `resume.md`, whichever exists; use pdftotext
or pypdf for PDF). For each new posting, fetch the description and ask
Claude via the Anthropic API (model claude-sonnet-4-6, or whatever model
string works for this account) for a strict JSON verdict:

  {"score": 1-5,
   "hard_requirements_missing": [...],
   "why": "two sentences max",
   "sponsorship_note": "if the posting mentions sponsorship/visa/citizenship, quote it, else null",
   "apply": true/false}

Score 5 means I clearly meet the must-haves; 3 means plausible with a
tailored resume; 1 means don't bother. Be blunt, no flattery. Store the
verdict back into the jobs.jsonl record. Cap this at 40 postings per run so
cost stays trivial, highest-priority terms first.

## Step 5: the digest (`digest.py`) and one command to run it all

`python run.py` runs poll then score then digest. The digest is a single
`digest.md` written to `digests/YYYY-MM-DD.md` and printed:

- Header with date, number of companies polled, number of new postings.
- Postings grouped by score (5 first), each as one line:
  company, title, location, posted_on, score, link, then the "why" indented.
- A short "missing hard requirements" line for anything scored 3 or 4.
- A footer listing companies that errored so I can fix them.

Also add `python run.py --days 3` to widen the window for the first run,
since seen.json is empty today.

## Step 6: schedule it

Show me a cron line (or a Claude Code desktop scheduled task) that runs
`python run.py` at 7:30 AM local time daily and appends stdout to
`logs/run.log`. Don't install it, just show it and I'll confirm.

## Step 7: first real run

Run `python run.py --days 3`, show me the digest, and list any company that
failed verification or polling. Then stop and wait for my feedback before
touching the code further.

## Rules

- Never fire more than one request at a time. Politeness over speed.
- No scraping the HTML site, JSON endpoint only.
- Never invent field names silently; if Workday's shape differs, print a
  sample of the raw response and adapt.
- Keep every file under ~150 lines. If something grows past that, split it.
- Do not push anything to a remote. Local git only for now.
