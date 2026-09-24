# Configuration

Two files control what the radar looks for: `config.json` holds the rules, and `companies.json` lists the
employers. Both are read at the start of each `python run.py`, so a change takes effect on the next run. The web
app reads `config.json` only when you paste a Workday URL into Tailor, and it reads it fresh each time, so it never
needs a restart for either file.

Current values below are as of 2026-09-24.

## config.json

### What gets searched

| Key | Current | What it does |
| --- | --- | --- |
| `search_terms` | data engineer, data scientist, machine learning, AI engineer | Searches sent to every employer. Workday matches them against the whole posting, so each one returns many loose hits that the title rules then remove. |
| `entry_terms` | early career, new college grad, entry level | Extra searches for tier 1 and 2 employers only. Each gets one page of results. |
| `max_days_ago` | 1 | How recent a posting must be, in days, for the role searches. `python run.py --days 3` overrides it for one run. |
| `entry_max_days_ago` | 14 | The same limit for the entry searches. Junior roles stay open for weeks and come back sorted by relevance rather than date, so they get a wider window. Postings already seen are never stored twice. |
| `max_pages_by_tier` | tier 1: 3, tier 2: 2, tier 3: 1 | How many pages of 20 results each role search reads, by employer tier. |
| `tier3_weekdays` | 0, 3 | Days tier 3 employers are polled, where 0 is Monday. `python run.py --all-tiers` polls them on any day. |

**Run time** grows with every term and page. Each request waits 1.5 seconds, so one more role term costs
roughly one request per page per employer. `python -m companies.report_companies` prints the estimated run
time for the current settings.

### Which titles are kept

The title rules run in this order, before any detail is fetched.

1. **The title must name a target role**, when `title_must_match_term` is true. A title passes if it matches one
   of `title_patterns`. If the title also has entry wording (junior, associate, new grad, early career,
   graduate, or Engineer I), it may match `entry_title_patterns` instead.
2. **An override word keeps it**, even if a word in step 3 would remove it. `include_override` lists these.
   Director, vice president, manager, principal, intern and co-op titles are never rescued.
3. **A seniority or domain word removes it.** `exclude_seniority` and `exclude_domain` list these.

| Key | Current | How it matches |
| --- | --- | --- |
| `title_patterns` | 23 patterns, for example `data engineer`, `data scien`, `\bml\b`, `analytics` | Case-insensitive regular expressions, searched anywhere in the title. In JSON a word boundary is written `\\b`. A plain phrase like `data scien` works as a substring. |
| `entry_title_patterns` | `software (engineer\|developer)`, `data` | Extra patterns allowed only for titles with entry wording. |
| `include_override` | data scientist, junior; new college grad; early career; associate | Case-insensitive substrings. |
| `exclude_seniority` | sr, lead, principal, staff, director, manager, architect, intern, head and others | Whole words or phrases, case-insensitive, so `lead` does not match `leadership`. Titles with "Senior" spelled out are kept on purpose; the six-year gate handles those. |
| `exclude_domain` | verification, packaging, devops, security, quality, firmware, mobile and others | Whole words or phrases, case-insensitive. |
| `title_must_match_term` | true | Turns step 1 off when false. Not recommended: most search hits are unrelated titles. |

### Where

| Key | Current | What it does |
| --- | --- | --- |
| `us_only` | true | Drops postings whose listed location or detail record puts them outside the US. A posting with a US location among several still passes. |

### Scoring and preparation

| Key | Current | What it does |
| --- | --- | --- |
| `score_cap` | 40 | The most postings sent to Claude in one run. Entry-level titles and postings asking two years or fewer go first, then the newest. Unscored postings wait for the next run. |
| `prepare_cap` | 0 | How many Apply postings get a tailoring plan made in advance after the run. 0 turns it off; plans are made on demand from the chat or Tailor. |

## companies.json

One entry per employer.

| Field | Meaning |
| --- | --- |
| `name` | Display name. Postings are stored as `name` plus requisition id, so renaming an employer makes its old postings look new. |
| `tenant`, `shard`, `site` | The Workday address, as in `https://<tenant>.<shard>.myworkdayjobs.com/<site>`. Taken from a real posting URL, never guessed. |
| `tier` | 1 and 2 are polled daily, 3 on the `tier3_weekdays`. Tier also sets search depth through `max_pages_by_tier`. |
| `sponsors_h1b` | The default when a posting says nothing about sponsorship: true reads as likely, false as unlikely, null as unknown. Posting text always wins over it. |
| `sponsorship_source` | Where the default came from, for example a fiscal 2025 filing count. |
| `extra_terms` | Optional searches for this employer only, for example `New College Grad 2026` at NVIDIA. |
| `verified`, `verified_at`, `open_roles` | The last live check of the address and how many roles it listed then. |

**Edit tier and sponsorship in the source lists, not in this file.** `python -m companies.expand` rebuilds
`companies.json`. It always recomputes `tier` and `sponsorship_source`, and it recomputes `sponsors_h1b` for any
employer named in its lists, so hand edits to those fields are lost the next time it runs. To change them durably:

- Sponsorship: the lists at the top of `companies/expand.py` are checked first, in this order: `NO_SPONSOR`, the
  hand-seeded list, `H1B_TOP`. Then `companies/h1b_check.json`, which records a filing count as evidence. An
  employer in none of them keeps whatever value it already has.
- Tier: add the employer to `TIER1` in `companies/expand.py`; it takes effect only if the employer sponsors.
  Other sponsoring employers are tier 2 and the rest tier 3.

`extra_terms` and the Workday address are kept across rebuilds.

### Adding an employer

1. Find one of its postings on `myworkdayjobs.com` and read the tenant, shard and site from the URL.
2. Record it: `python -m companies.ledger set "Name" tenant shard site`.
3. Check it against the live site: `python -m companies.resolve`.
4. Rebuild the list: `python -m companies.expand`, then `python -m companies.report_companies`.

## Fixed in code

These rules are not settings. Changing them means changing the code, with a test.

| Rule | Where |
| --- | --- |
| Six or more years of required experience: scored 1 without calling Claude, so it never reaches Apply | `radar/poll.py`, `radar/score.py` |
| Sponsorship phrases that mean no, and PERM-style ads | `radar/sponsor.py` |
| Apply needs a best score of 4 and a sponsoring posting or default; Entry level takes entry titles scoring 3 | `radar/digest.py` |
| 1.5 seconds between Workday requests, and a 6-hour response cache | `radar/wd.py` |

## Common adjustments

- **The shortlist is thin.** Run `python run.py --days 3 --all-tiers` once. For a lasting change, raise
  `max_days_ago` to 2 before adding search terms, which cost more run time.
- **Too many senior roles.** Add the word to `exclude_seniority`, add an example title to the cases in
  `tests/test_titles.py`, and run `python -m pytest -q tests/test_titles.py`.
- **A target role is missing.** Add a pattern to `title_patterns`, and a search term only if Workday's search
  does not already return those postings.
- **A run takes too long.** Lower `max_pages_by_tier` for tier 2 before removing search terms.
