# Changelog

## Unreleased

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
