# Changelog

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
