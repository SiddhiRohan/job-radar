# Configuration

Two files control what the radar looks for: `config.json` holds the rules, and `companies.json` lists the
employers. Both are read at the start of each `python run.py`, so a change takes effect on the next run. The web
app reads `config.json` only when you paste a Workday URL into Tailor, and it reads it fresh each time, so it never
needs a restart for either file.

Current values below are as of 2026-09-24.

## Your resume and profile

Put your resume in the `Resume/` folder. Any of these works:

| Layout | Files | What the radar does |
| --- | --- | --- |
| One resume | `Resume/resume.docx` | Scores every posting against it, framed once as early-career and once as experienced |
| Two resumes | `Resume/entry.docx` and `Resume/experienced.docx`, or any names starting with those words | Scores each posting against both and recommends one |
| Folder tree | `Resume/Entry/1 Page/<file>` and `Resume/Experienced/V1/<role>/<1 Page or 2 Page>/<file>`, with the file name set as `RESUME_FILENAME` in `.env` | Also recommends a role folder and a length, and tailors from that variant |

Word files (`.docx`) are needed for tailoring; a `.txt` or `.md` resume is enough for scoring. `profile.md` is
optional: a few lines on your target roles, strengths and tools you do not have make the scores sharper. Without
it the resume alone is used.

## config.json

### When it runs

| Key | Current | What it does |
| --- | --- | --- |
| `auto_run` | true | While the web app is open it runs the radar once a day at `run_time`. If the computer was off or asleep then, it runs as soon as the app opens. A failed start waits two hours before trying again. |
| `run_time` | 07:30 | Local time of the daily run. |

To run even when the app is closed, turn on **Every morning** on the Setup page, or run
`python -m radar.schedule install` (and `remove` or `status`). It uses the computer's own scheduler: a Task
Scheduler task named JobRadar on Windows, a launchd agent on macOS, a cron line on Linux, each starting `run.py` at
`run_time` and appending to `logs/run.log`.

Only one run happens at a time, whoever starts it: the web app, the operating system's scheduler or a terminal.
A second one sees the lock in `.cache/run.lock` and steps aside. A lock older than four hours is treated as left
behind by a machine that shut down mid-run.

### What gets searched

| Key | Current | What it does |
| --- | --- | --- |
| `search_terms` | data engineer, data scientist, machine learning, AI engineer, analytics | Searches sent to every Workday employer. Workday matches them against the whole posting, so each one returns many loose hits that the title rules then remove. A job board has no search: every posting on it goes through the title rules instead. |
| `entry_terms` | early career, new college grad, entry level | Extra searches for tier 1 and 2 employers only. Each gets one page of results. On a job board they widen the date window only for titles with entry wording. |
| `max_days_ago` | 1 | How recent a posting must be, in days, for the role searches. `python run.py --days 3` overrides it for one run. |
| `entry_max_days_ago` | 14 | The same limit for the entry searches. Junior roles stay open for weeks and come back sorted by relevance rather than date, so they get a wider window. Postings already seen are never stored twice. |
| `max_pages_by_tier` | tier 1: 3, tier 2: 3, tier 3: 2 | How many pages of 20 results each role search reads, by employer tier. |
| `tier3_weekdays` | 0 to 6, every day | Days tier 3 employers are polled, where 0 is Monday. `python run.py --all-tiers` polls them on any day. |

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
| `exclude_seniority` | lead, principal, staff, director, manager, architect, intern, head and others | Whole words or phrases, case-insensitive, so `lead` does not match `leadership`. Titles with "Senior" or "Sr" are kept on purpose: they score 4 as often as the rest, and the six-year gate handles the ones that are really senior. |
| `exclude_domain` | verification, packaging, devops, security, quality, firmware, mobile and others | Whole words or phrases, case-insensitive. |
| `title_must_match_term` | true | Turns step 1 off when false. Not recommended: most search hits are unrelated titles. |

### Where

| Key | Current | What it does |
| --- | --- | --- |
| `us_only` | true | Drops postings whose listed location or detail record puts them outside the US. A posting with a US location among several still passes. Lever and Ashby give each place's country, which decides; Greenhouse gives only the place's words. |

### Scoring and preparation

| Key | Current | What it does |
| --- | --- | --- |
| `score_cap` | 120 | The most postings sent to Claude in one run. Entry-level titles and postings asking two years or fewer go first, then the newest. Unscored postings wait for the next run. |
| `prepare_cap` | 0 | How many Apply postings get a tailoring plan made in advance after the run. 0 turns it off; plans are made on demand from the chat or Tailor. |

### How a fit is judged

Claude returns the E and X scores (1 to 5, one per resume base) together with four factors. Each factor is marked
meets, partial or gap, and carries what the posting asks and the resume evidence that answers it, 20 words at most
each, plus a short note. The factors are written first and the scores must agree with them.

| Factor | What it judges |
| --- | --- |
| Experience | Years and depth in the same kind of work the role needs, against the better-fitting resume base. Shared keywords alone do not count. |
| Level | Whether the posting's seniority fits the entry or the experienced base. |
| Skills | The must-have skills the resume proves. When one is missing, the note names the most important, as "Missing: Databricks." |
| Domain | Familiarity with the industry or problem area. |

Three more are read by rule from the stored posting, with no model call:

| Factor | Meets | Partial | Gap |
| --- | --- | --- | --- |
| Sponsorship | The posting or the company default sponsors, or Claude read the posting as sponsoring | Neither says | The posting says no or reads as a PERM ad, Claude read it as no, or the company default is no and neither the posting nor Claude says yes |
| Location | Any US location; the note says remote or hybrid when the location or clear wording in the posting does | No location | Outside the US |
| Pay | A range is stated (`radar/salary.py`) | Not listed | Never: there is no pay target to miss |

Sponsorship uses the same test as the digest's Skipped and Apply sections, so its badge never disagrees with the
section a posting is in. The posting drawer shows all seven above the description, and Apply and Entry level rows in
the digest get a line such as `gaps: skills (Databricks), domain`. Postings scored before the factors existed keep
their old verdict, with no table and no gaps line. Postings decided by rule (years gate, sponsorship no, PERM ad)
never reach Claude, so they show only the three rule rows.

## companies.json

One entry per employer, either on Workday (`tenant`, `shard`, `site`) or on a job board (`ats`, `board`).

| Field | Meaning |
| --- | --- |
| `name` | Display name. Postings are stored as `name` plus requisition id, so renaming an employer makes its old postings look new. |
| `tenant`, `shard`, `site` | The Workday address, as in `https://<tenant>.<shard>.myworkdayjobs.com/<site>`. Taken from a real posting URL, never guessed. |
| `ats`, `board` | An employer on a job board instead: `ats` is `greenhouse`, `lever` or `ashby`, and `board` is the token in the board's URL (`job-boards.greenhouse.io/<board>`, `jobs.lever.co/<board>`, `jobs.ashbyhq.com/<board>`). An entry without `ats`, or with `"ats": "workday"`, is a Workday one. For a board employer the requisition id is the board's posting id. |
| `tier` | 1 and 2 are polled daily, 3 on the `tier3_weekdays`. Tier also sets search depth through `max_pages_by_tier`, and only tiers 1 and 2 get the entry terms. |
| `sponsors_h1b` | The default when a posting says nothing about sponsorship: true reads as likely, false as unlikely, null as unknown. Posting text always wins over it. |
| `sponsorship_source` | Where the default came from, for example a fiscal 2025 filing count. |
| `extra_terms` | Optional searches for this employer only, for example `New College Grad 2026` at NVIDIA. |
| `verified`, `verified_at`, `open_roles` | The last live check of the address and how many roles it listed then. |

**A job board is read whole.** Greenhouse, Lever and Ashby list every open posting with its description in one
response, so a board costs one request per run and nothing more is fetched for a new posting. Each posting then goes
through the rules a Workday search result does: the title must match `title_patterns` (or `entry_title_patterns`
with entry wording), it must be within `max_days_ago` (`entry_max_days_ago` for a title with entry wording, tiers 1
and 2), and the seniority, domain and US rules apply.

**Edit tier and sponsorship in the source lists, not in this file.** `python -m companies.expand` rebuilds
`companies.json`. It always recomputes `tier` and `sponsorship_source`, and it recomputes `sponsors_h1b` for any
employer named in its lists, so hand edits to those fields are lost the next time it runs. To change them durably:

- Sponsorship: the lists at the top of `companies/expand.py` are checked first, in this order: `NO_SPONSOR`, the
  hand-seeded list, `H1B_TOP`. Then `companies/h1b_check.json`, which records a filing count as evidence. An
  employer in none of them keeps whatever value it already has.
- Tier: add the employer to `TIER1` in `companies/expand.py`; it takes effect only if the employer sponsors.
  Other sponsoring employers are tier 2 and the rest tier 3. A job-board employer added with unknown sponsorship
  starts in tier 2, and a rebuild moves it to tier 3 like any other unless its filings are recorded in
  `companies/h1b_check.json`.

`extra_terms`, the Workday address and the job board are kept across rebuilds. `python -m companies.verify`
rechecks Workday entries only; a board employer shows as SKIP there, and running `python -m companies.board` again
with the same name rechecks it.

### Adding an employer

On Workday:

1. Find one of its postings on `myworkdayjobs.com` and read the tenant, shard and site from the URL.
2. Record it: `python -m companies.ledger set "Name" tenant shard site`.
3. Check it against the live site: `python -m companies.resolve`.
4. Rebuild the list: `python -m companies.expand`, then `python -m companies.report_companies`.

On Greenhouse, Lever or Ashby:

1. Follow any job on the employer's careers page to its board. The address names the board:
   `job-boards.greenhouse.io/<board>/jobs/...` (older links use `boards.greenhouse.io`), `jobs.lever.co/<board>/...`
   or `jobs.ashbyhq.com/<board>/...`. A careers page on the employer's own domain often hides the board; a
   Greenhouse one shows `gh_jid=` in its job links, and the board token is then usually the company name.
2. Add it: `python -m companies.board "Name" <that address>`. It reads the board once, prints how many postings
   are open, and writes the entry as verified, with sponsorship from the lists above and a tier.
3. Refresh the report if you want it: `python -m companies.report_companies`.

A board with no open postings is usually one the employer stopped using, and the command says so. Boards on
Lever's or Greenhouse's EU hosts are not supported.

## Email: statuses from hiring emails

The run and the **Check mail** button on Applied read your Gmail over IMAP and move application statuses. It is
read-only: the mailbox is opened with IMAP's read-only mode and messages are fetched without marking them read.
Nothing is sent, moved or deleted.

**Setting it up.** Gmail needs an app password, a separate 16-character password for one app:

1. Turn on 2-Step Verification for the Google account, if it is not on already.
2. Create an app password at https://myaccount.google.com/apppasswords and name it "Job radar".
3. Add two lines to `.env`, which git ignores:

   ```
   GMAIL_ADDRESS=you@gmail.com
   GMAIL_APP_PASSWORD=the16characterpassword
   ```

4. Press **Check mail** on Applied, or wait for the next `python run.py`.

The password works with or without the spaces Google shows between its four groups.

Revoke the app password on the same Google page at any time; the step then turns itself off.

**What it does with an email.** Only messages since the first application are read, and your own sent mail is
skipped.

| The email | What happens |
| --- | --- |
| Contains the requisition id of exactly one application, and the wording is clear | The status moves on its own, forward only: applied, screen, interview, rejected, offer. An older email never moves a status back. |
| A rejection with no requisition id that names the role of exactly one application at that employer ("applying for the Data Engineer II position") | Moves to rejected on its own. A title inside a longer one does not count: "Data Scientist" is not "Senior Data Scientist" or "Data Scientist I". Only the subject and the first 1,500 characters are read, so job suggestions in a footer never match. |
| A rejection for a role that is not on your list, or from an employer where nothing is open | Kept under "Rejections for roles not on your list" on the Email card. Nothing to do. |
| Could change a status (an offer, an invitation to a screen or interview, or a rejection that names no role or a title several applications share) but has no requisition id, ids of several applications, or mixes an invitation with a plain confirmation | Needs review, with likely applications listed first |
| A plain confirmation, or account, password and task mail | Ignored: it cannot move anything past applied |
| Anything else | Ignored |

**How wording is read.** A rejection needs phrases such as "decided to move forward with other candidates",
"decided not to move forward", "regret to inform", "won't be able to move forward", "aren't moving forward", "does not
align with" or "pursuing other applicants". An interview or screen needs
invitation wording, such as "we would like to invite you to interview" or "schedule a phone screen"; the bare word
"interview" is not enough, because confirmations mention interviews as a possible next step. Any phrase shortly after
"if", "may", "might" or "should" is ignored, so "if you are selected for an interview" and "if you are not selected"
change nothing.

After a rule change, `python -m radar.mail --recheck` reads every email in Needs review again and decides it with the
current rules.

Each update and review item links to the email in Gmail. Seen message ids, recent updates and the review list are
kept in `.cache/ui/mail.json`, with a short snippet of each email; the full text is never stored.

## Postings since you applied

Once a day, after the email step, `radar/watch.py` re-reads the posting behind every application that is not
already rejected or at offer, one request per posting at the usual 1.5 second gap. It records, with the date first
seen, whether the posting closed (Workday answers "permission denied" for a posting that was taken down), was
retitled, changed its pay range, or had its description rewritten. The Applied page shows closed postings with the
days since you applied, and changed ones with what changed; "Check postings" runs it now. State lives in
`.cache/ui/watch.json`. Nothing here changes a status: a closed posting is a hint, not a rejection. Postings from
job-board employers are not re-read yet and count as unknown.

## Fixed in code

These rules are not settings. Changing them means changing the code, with a test.

| Rule | Where |
| --- | --- |
| Six or more years of required experience: scored 1 without calling Claude, so it never reaches Apply | `radar/poll.py`, `radar/score.py` |
| Sponsorship phrases that mean no, and PERM-style ads | `radar/sponsor.py` |
| Apply needs a best score of 4 and a sponsoring posting or default; Entry level takes entry titles scoring 3 | `radar/digest.py` |
| The scoring prompt, the four model factors, and the sponsorship, location and pay rules | `radar/fit.py`, `radar/factors.py` |
| 1.5 seconds between requests to Workday or a job board, and a 6-hour response cache | `radar/wd.py` |
| How each job board's fields are read: dates, places, pay, description | `radar/boardparse.py` |

## Common adjustments

- **The shortlist is thin.** Run `python run.py --days 3 --all-tiers` once. For a lasting change, raise
  `max_days_ago` to 2 before adding search terms, which cost more run time.
- **Too many senior roles.** Add the word to `exclude_seniority`, add an example title to the cases in
  `tests/test_titles.py`, and run `python -m pytest -q tests/test_titles.py`.
- **A target role is missing.** Add a pattern to `title_patterns`, and a search term only if Workday's search
  does not already return those postings.
- **A run takes too long.** Lower `max_pages_by_tier` for tier 2 before removing search terms.
