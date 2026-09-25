# Changelog

## Unreleased

**Email rules recalibrated.** Interview and screen need invitation wording; conditional phrases ("if you are selected
for an interview") are ignored; plain confirmations and account mail are skipped instead of sent to review.

**Statuses from hiring emails.** `radar/mail.py` reads Gmail over IMAP, read-only, with an app password from `.env`.
An email carrying the requisition id of exactly one application, with clear wording, moves that application forward
on its own; anything else that looks like hiring mail lands in a needs-review list on Applied, with likely
applications first. Runs in the daily pipeline and from a Check mail button. Application storage moved into
`radar/applications.py` so the server and the mail step share it.

**Pay on every posting.** `radar/salary.py` reads the pay range from the posting text, since Workday has no pay
field. It handles the common formats (commas or none, K suffix, USD prefix, hourly rates, several ranges by
location) and ignores money that is not pay, such as bonuses, revenue and placeholder ranges. 82% of stored postings
carry a range. Today cards and digest lines show it, or "Pay not listed".

**49 more companies.** `companies.json` grows from 113 to 162 verified Workday tenants, among them Samsung, TD Bank,
Zillow, Procter & Gamble, NXP, AIG, Chubb, TransUnion, Sanofi, Yahoo, Zendesk, F5, FICO and Nationwide. Every tenant
came from a posting URL seen in search results and passed a live check. "head" joins the seniority exclusions.
Sponsorship defaults for all 49 come from a fiscal 2025 LCA lookup recorded in `companies/h1b_check.json`.

**Capital One and per-posting sponsorship.** Capital One is a tier 1 sponsor; a posting the scorer reads as
sponsoring now reaches Apply even under a negative company default. The Today view lists Skipped postings, collapsed.

**UI refresh.** Mark applied updates its row in place and collapsed sections stay open. Design tokens, a type scale
and a dark mode that follows the system. Rows are cards with a score badge tinted by fit, and section headings stay
pinned while scrolling. Placeholder cards while loading, a fade when a section opens, and empty and error states that
name the next step. A radar mark in the header and empty states, and an SVG favicon.

**README.** Rewritten with a banner, screenshots in light and dark, a pipeline diagram, a quickstart and a
configuration table. Screenshots are taken from a demo copy with neutral fit notes and made-up applications.

**Applied as a dashboard.** The Applied view shows headline tiles (applications, last 7 days, companies, heard
back), applications per day for the last 14 days, where applications stand, the companies applied to most, and a
board where changing a status moves the card. Plain SVG and CSS in `web/applied.js`, chart color checked with the
dataviz palette validator in both modes. The full table stays one click away.

## v0.3 (2026-09-20)

**Outreach in Tailor.** Write outreach builds a note and a message from the visible resume sections, both editable
with live counts, saved into outreach.md alongside the resume.

**Entry level section.** Junior and new-grad postings scoring 3 or better appear under Apply in the digest and the
UI instead of the collapsed tail. The digest now selects a day's postings by date, so a second run on the same day
no longer reports an empty day.

**Entry-level sourcing.** Titles must match a role pattern instead of one loose word of the search term; entry
search terms ("early career", "new college grad", "entry level") with a 14-day window on tier 1 and 2; entry-level
rows scored first; override words no longer rescue director or intern titles. Overlapping runs store each posting
once (`radar/store.py`).

## v0.2 (2026-09-15)

**Web UI.** `server.py` (FastAPI) plus vanilla `web/`: Today (ranked shortlist with the score at the left edge,
Apply / Maybe / Contract / Everything else, Mark applied, Run the radar), Tailor (side-by-side editor with
changed-word highlighting, moved markers, inline notes, rebuild, save to folder with a native Browse dialog, cover
letter), Applied (`applications.md` as a table with inline status). Plans cached per posting.

**Chat assistant.** A drawer with a tool-using assistant that can switch views, refresh, run the radar, mark
applied, set status, open a posting in Tailor, edit tailored text, plan / build / save a resume on demand, and save
durable notes to `memory.md`. Threads persist on disk; minimize to a pill; thread list with New chat and Delete.

**Sourcer first.** Pre-planning off by default; Today rows carry no Tailor button; tailoring is on demand via chat.

**Fixes.** Sponsorship: seven more no-sponsorship phrases and the model's own "no" verdict both send a posting to
Skipped (Caterpillar case). Rewrites copy the dominant run's formatting and finalize skips headers and hyperlinks
(3pt project header). Workday URL parser strips the `-1` revision suffix.

**Repo.** Modules grouped into `radar/`, `tailoring/`, `companies/`, `docs/`. CLAUDE.md working rules, PR template,
pre-commit (ruff, gitleaks, whitespace), 38 offline tests, GitHub Actions CI, issues #1 to #7 as backlog.


## v0.1 (2026-09-13)

Rounds 1 and 2 of the job radar, pipeline only (no UI yet).

**Round 1: the radar.** Workday JSON client with caching, polite retries, and correct paging (Workday only
reports `total` on the first page). Seed list verified against live tenants; five companies found to be off
Workday. Poller with title, US, and search-term filters, `seen.json` and `jobs.jsonl` tracking. Claude scorer with a
strict JSON verdict. Daily digest and `run.py`. 7:30 AM Task Scheduler entry.

**Round 2: personal and stricter.** `profile.md` in every prompt. Sponsorship tagging from posting text
(no / yes / PERM ad / unknown) with per-company defaults. Seniority and domain title lists with an include
override. Years-of-experience gate at 6+. Real US check from the detail record. Two-resume scoring (entry and
experienced bases) with a fuller verdict. `apply.py` tailoring with locked facts, a confirmed-skills vocabulary,
fabrication guards, cover letters, and outreach. `finalize.py` humanize and de-mark pass. Company list expanded
from 15 to 113 verified Workday tenants with sponsorship source and tiers; tiered polling under 30 minutes a
day. Sponsorship regex extended; the model's own "no" also skips a posting.
