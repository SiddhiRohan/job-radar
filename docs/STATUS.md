# STATUS

## Current state (2026-09-27)

Live and in daily use. The 7:30 AM Task Scheduler entry "JobRadar" runs poll, score, digest, then mail (statuses
from hiring emails) and watch (the posting behind every open application). Prepare is off, so tailoring happens on
demand. The UI runs with `python server.py`. Everything is merged to `main` on the private repo.

- Sourcing covers 162 verified Workday tenants (48 tier 1, 77 tier 2, 37 tier 3). Since PR #54 every tier is polled
  daily, tier 1 and 2 read three pages per search and tier 3 two, five role terms (analytics joined) plus three
  entry-level terms, and "Sr" no longer removes a title. The estimated search phase is about an hour. Target set by
  the owner: at least 30 score-4 postings a day; the 2026-09-28 run is the first at these settings. Before it, days
  kept 35 to 101 postings with 6 to 14 scoring 4, and nothing went unscored, so the score cap was not the limit.
- Applications recorded through the UI: 120, of which 11 rejected and none with a reply yet. 18 emails without a
  requisition id wait in Needs review. The posting watcher found 81 postings still open and 15 closed with no reply.
- Two agents run on the applications: "What the rejections say" (rejection rate by title family, seniority, resume
  base, fit score, years asked, sponsorship default, company) and "Postings since you applied" (closed, retitled,
  repriced, rewritten).
- UI round of 2026-09-26 and 27: Undo from the toast for Mark applied, status changes and settled emails; keyboard
  shortcuts on Today (`?` lists them); filter chips; a motion pass; glass header, score rings and Instrument Sans;
  a command palette on Ctrl+K. Vanilla HTML, CSS and JavaScript throughout, no framework.
- The chat assistant can check mail, report rejection patterns and posting status, plan and build a tailored
  resume, and drive the page.
- Brand: 3D logo, six-second ident, favicons and a social preview image in docs/img. The owner's name, resume file
  name and personal stopwords live in `.env` (`radar/owner.py`), never in tracked files.
- Workflow: branch and PR for every change, CI (ruff, pytest) on PRs and main, pre-commit locally, 156 offline
  tests, 47 merged PRs. Commits and merges carry no attribution trailers. Branch protection is unavailable on the
  free private plan; the rule lives in CLAUDE.md. Never stack PRs.
- Known gaps: hosting is still the laptop (issue #4); Google and the other 95 employers in
  `companies/not_on_workday.json` need a non-Workday adapter (issue #1); several sourced new-grad roles are 2027
  start dates; the social preview image must be uploaded by hand in repository settings; open issues are #1 to #6,
  #16 and #17.

The sections below are kept as history. Dates in them are the dates they were written.

## State recorded on 2026-09-25

Live and in daily use. The 7:30 AM Task Scheduler entry "JobRadar" runs poll, score, digest, then the two
follow-up steps: mail and watch. Prepare is off, so tailoring happens on demand.

- Sourcing covers 162 verified Workday tenants (48 tier 1, 77 tier 2, 37 tier 3), tiers 1 and 2 daily and tier 3 on
  Mondays and Thursdays. Four role search terms plus three entry-level terms with a 14-day window. Every posting
  shows a pay range when the description has one (about 82 percent do).
- Recent runs kept 80 (09-22), 94 (09-23), 101 (09-24, a tier-3 day), 49 (09-25), with 4 to 13 in Apply each day.
- Applications recorded through the UI: 107, of which 11 rejected and none with a reply yet. Rejections arrive by
  email and are applied automatically when the email carries exactly one known requisition id and clear wording;
  18 emails without an id wait in Needs review on the Applied page.
- Two agents run on the applications. "What the rejections say" compares rejection rates by title family, seniority,
  resume base, fit score, years asked, sponsorship default and company (counts only, three-rejection floor).
  "Postings since you applied" re-reads each open posting daily: 81 still open, 15 closed without a reply.
- The chat assistant can check mail, report rejection patterns and posting status, plan and build a tailored
  resume, and drive the page.
- Brand: 3D logo, six-second ident, favicons and a social preview image in docs/img. The owner's name, resume file
  name and personal stopwords live in `.env` (`radar/owner.py`), never in tracked files.
- Workflow: branch and PR for every change, CI (ruff, pytest) on PRs and main, pre-commit locally, 154 offline
  tests, 38 merged PRs. Branch protection is unavailable on the free private plan; the rule lives in CLAUDE.md.
  Never stack PRs.
- Known gaps: hosting is still the laptop (issue #4); several sourced new-grad roles are 2027 start dates; the
  social preview image must be uploaded by hand in repository settings; open issues are #1 to #6, #16 and #17.


## State recorded on 2026-09-20

Live and in daily use. The 7:30 AM Task Scheduler entry "JobRadar" runs poll, score and digest; prepare is off, so
tailoring happens on demand. The UI runs with `python server.py`. Everything is merged to `main` on the private repo.

- Sourcing covers 162 verified Workday tenants (49 added 2026-09-20, each checked against fiscal 2025 H-1B filings), tiers 1 and 2 daily and tier 3 on Mondays and Thursdays. Four role
  search terms plus three entry-level terms, with a 14-day window on the entry terms.
- Recent runs: 2026-09-17 kept 176, 2026-09-18 kept 91, 2026-09-19 kept 49, 2026-09-20 kept 0 (a Sunday; 83 removed
  by rule, nothing fresh posted).
- Applications recorded through the UI: 38 as of 2026-09-20.
- Today's shortlist has an Entry level section between Apply and Maybe, for junior postings scoring 3 or better.
  Junior roles rarely score 4, so before this they sat in the collapsed tail and were never seen.
- Direction: the sourcer is the product; resume tailoring is on demand through the chat drawer, with the Tailor view
  kept for the side-by-side and outreach. Multi-user is parked until the owner asks.
- Workflow: branch and PR for every change, CI (ruff, pytest) on PRs and main, pre-commit locally, 70 offline tests.
  Branch protection is unavailable on the free private plan; the rule lives in CLAUDE.md. Never stack PRs.
- Known gaps: hosting is still the laptop (the Actions plan in this session's notes is not built); several sourced
  new-grad roles are 2027 start dates, which do not suit a May 2026 graduate; backlog is GitHub issues #1 to #7.

## Outreach in Tailor (2026-09-17): issue #7

Write outreach uses the current visible resume sections and the existing background generator.
Both drafts are editable with accessible live counts
(note under 300 characters; message 100–120 whitespace-delimited words). Save to folder writes the latest
drafts and counts into outreach.md without another rebuild. Retry and stale-response guards are included.

Outreach failures use the existing toast, guarded against stale responses, and re-enable Write outreach
for retry. Tailor has no inline outreach error paragraph: after a successful manual Retry replaces an
offline failure, the original five-second timer no longer finds an outreach `.error` element and therefore
does not retry again or discard subsequent resume edits. The existing offline retry machinery is unchanged.

## State recorded on 2026-09-15

Live and in daily use. The 7:30 AM Task Scheduler entry "JobRadar" runs poll, score, digest (prepare is off by
default); the UI runs with `python server.py`; everything is merged to `main` on the private repo.

- Runs so far: 2026-09-13 (catch-up, 113 companies, 242 kept), 2026-09-14 (113 companies, 23 kept, 1 Apply),
  2026-09-15 (93 companies on a non-tier-3 day, 112 kept, 5 Apply, 476 removed by rule).
- Applications recorded through the UI: 23 as of 2026-09-15 11:23, across HPE, Netflix, NVIDIA, Adobe, Ally, Applied
  Materials, Bank of America, Cardinal Health, Disney, Freddie Mac, Visa, Home Depot, Humana, KLA, Lowe's, Mastercard,
  McKesson, Thomson Reuters, Walmart, Workday.
- Direction: the sourcer is the product; resume tailoring is on demand through the chat drawer (plan, build, save),
  with the Tailor view kept for the side-by-side. Multi-user is parked until the owner asks.
- Workflow: branch and PR for every change, CI (ruff, pytest) on PRs and main, pre-commit locally. Branch protection
  is not available on the free private plan; the rule is in CLAUDE.md. Do not stack PRs (see DECISIONS.md).
- Backlog: GitHub issues #1 to #7.

The sections below are the round-2 report as written on 2026-09-13 and are kept for history; "not installed" and
"nothing pushed" lines are superseded by the state above.

## Round 2 report (2026-09-13, run unattended)

## Completed

- **Housekeeping.** Remote confirmed private (`gh repo view` -> private: true). Nothing pushed this round. `.gitignore`
  covers Resume/, profile.md, jobs.jsonl, seen.json, last_run.json, digests/, .cache/, logs/, .env, and the stray root
  resume file. Dell, AMD, Qualcomm, Deloitte, JPMorgan Chase removed from companies.json. Cap was 120 for the Part B
  run and is back to 40 (`score_cap` in config.json).
- **Part A.** `profile.md` written verbatim; `score.py` puts it in the cached system prompt on every run.
- **Part B.** Key confirmed set (`ANTHROPIC_API_KEY set: True`, never printed). The earlier "unscored for everything"
  was a 400 from `minimum`/`maximum` in the JSON schema; fixed with an enum. 5 postings scored end to end before the
  full run. Sponsorship tagging (`sponsor.py`), `sponsors_h1b` seeded per company, new title lists with
  `include_override`, years gate, detail-record US check (real fields: `location`, `additionalLocations`,
  `jobRequisitionLocation.country.alpha2Code`), URL-path city check, two-resume scoring with the new verdict schema,
  `RESUME_MAP.md`, new digest layout. Files: filters.py, sponsor.py, resumes.py, poll.py, score.py, digest.py, wd.py.
- **Part C.** `apply.py`, `tailor.py`, `plan.py`, `letters.py`, `RESUME_RULES.md`. Ran on the top Apply posting,
  Adobe R171718 Machine Learning Engineer. Output in `Resume/For Adobe/R171718_Machine-Learning-Engineer/`:
  `jd.txt`, the tailored resume docx, `outreach.md`, `notes.md` (fit assessment, every before/after
  change, hard-to-defend flags, questions, overlap explanations). No cover letter: the posting does not ask for one.
- **Part D.** `finalize.py` ran on that folder: humanized 12 of 38 prose paragraphs (diff in notes.md), invisible
  Unicode stripped (0 in the docx, 5 in jd.txt), docx author/lastModifiedBy/app properties cleared. Report appended
  to notes.md. Digests were also swept.
- **Part E.** Schedule shown below, not installed.

## Skipped or changed, and why

- Approval gates skipped per your instruction; `--yes` used. Before/after is in notes.md.
- The first tailoring pass fabricated (scikit-learn, feature engineering, anomaly detection). I added guards and redid
  the run; see DECISIONS.md items 9. The summary can still combine existing words into new phrases ("fraud and abuse
  detection"), so read it once.
- First outreach draft cited scikit-learn and PyTorch; regenerated from the tailored resume text. The humanize pass
  shortened the message to 92 words (target 100 to 120), so add a sentence if you use it.
- remove-ai-marks service not running; exiftool and qpdf not installed. Local fallback used. No PDFs were produced.
- Cover letter path is implemented but untested on a real posting (none in Apply required one).
- Empty `AI Engineer` role folder untouched: the scorer recommended `DS and DE Resumes/two-page` for every Apply row.

## Part E: schedule (not installed)

Windows Task Scheduler, 7:30 AM local daily, output appended to logs/run.log:

    mkdir logs
    schtasks /Create /SC DAILY /ST 07:30 /TN "JobRadar" /TR "cmd /c cd /d C:\Users\siddh\Downloads\job-radar && python run.py >> logs\run.log 2>&1"

Cron equivalent (WSL or Mac):

    30 7 * * * cd /c/Users/siddh/Downloads/job-radar && python run.py >> logs/run.log 2>&1

## Part B header stats (3-day window, 15 companies)

    Companies polled: 15 | Window: last 3 day(s) | New postings kept: 117
    Removed by rule: seniority 242, domain 35, non_us 45, years_gate 17, sponsorship_no 38, perm_ad 0
    API calls: 68 (rule-decided postings skip the API) | Lower scores: score 3: 7, score 2: 21, score 1: 28 (years gate 10)
    Skipped section: 45 (all Booz Allen / Leidos clearance, Capital One no-sponsorship) | Errors: none

## Apply (6)

- **Adobe** | Machine Learning Engineer | San Jose | Posted 2 Days Ago | E3/X4 | experienced · DS and DE Resumes/two-page | https://adobe.wd5.myworkdayjobs.com/en-US/external_experienced/job/San-Jose/Machine-Learning-Engineer_R171718
- **Humana** | Senior Data Scientist | Louisville, KY | Posted 2 Days Ago | E2/X4 | experienced · DS and DE Resumes/two-page
    Hits nearly every must-have: production LLM/RAG, agentic-style systems, Python/SQL/PySpark, ETL, ML frameworks; clears Master's + 3 years.
- **KLA** | AI Software Engineer|Manufacturing | Ann Arbor, MI | Posted 3 Days Ago | E3/X4 | experienced · DS and DE Resumes/two-page
    RAG, LLM, data engineering, MLOps map well. Platform tools missing: Snowflake, Azure.
- **Mastercard** | Data Engineer II | O'Fallon, Missouri | Posted 3 Days Ago | E3/X4 | experienced · DS and DE Resumes/two-page
    ETL/ELT, SQL, Python, PostgreSQL, data modeling, data quality, AWS, Spark via EMR, plus payments domain. Platform tools missing: Databricks.
- **Target** | Data Engineer - Finance AI Solutions | Brooklyn Park, MN | Posted 2 Days Ago | E3/X4 | experienced · DS and DE Resumes/two-page
    Spark/PySpark, AWS, ETL, dbt, Airflow, FastAPI match; Scala/Java absent but not mandatory. Platform tools missing: GCP, Azure.
- **Walmart** | (USA) Senior, Data Scientist | Bentonville, AR | Posted 2 Days Ago | E2/X4 | experienced · DS and DE Resumes/two-page
    ML modeling, Python, SQL, experimentation, production deployment; main gap is mathematical optimization depth.

Full lines with links: digests/2026-09-13.md.

## Maybe (0)

No posting with sponsorship "unknown" scored 4 or higher. All 15 companies have a seeded `sponsors_h1b`, so
"unknown" only appears when a company is null; that will change once the expanded list adds null companies.

## Contract / backup (0)

## Company expansion (after STATUS.md was first written)

- Candidates: 209 (15 already verified + 194 new). Resolved from search-result URLs: 105. Verified: 98 new, 113 total.
  Failed twice and dropped: 7 (Chime, VMware, Verizon, Discover, Eli Lilly, Amplify, CMU). Not on Workday: 96, by ATS in
  `not_on_workday.json` and COMPANIES_REPORT.md. 58 of those got only one search: the session's web-search budget (200)
  ran out, see DECISIONS.md item 10.
- Tiers: 47 tier 1, 46 tier 2, 20 tier 3. `sponsors_h1b` true 93 / false 9 / null 11, each with `sponsorship_source`.
- Tier 3 polls on Monday and Thursday (`tier3_weekdays` in config.json, or `--all-tiers`). Pages per search by tier:
  3 / 1 / 1 (`max_pages_by_tier`). Estimate: about 37 min daily, 41 on tier-3 days. Measured: the run below took
  about 29 min wall time for 93 companies. The 30-minute target holds only at 1 page for tier 2; to get tier 1 to more
  pages, drop search terms or demote some tier-1 names.

### `python run.py --days 1` with the new list (Sunday, so tier 3 skipped)

    Companies polled: 93 | Window: last 1 day(s) | New postings kept: 6
    Removed by rule: seniority 20, domain 3, non_us 2, years_gate 2, sponsorship_no 0, perm_ad 0
    API calls: 4 | Apply: 1 (McKesson Data Scientist, USA Remote, E3/X4) | Maybe: 0 | Errors: none

The low count is a one-day window on a Sunday with one page per search for tier 2; the 3-day backlog for the 98 new
companies has not been polled. Run `python run.py --days 3 --all-tiers` once to catch up (expect 40+ minutes).
