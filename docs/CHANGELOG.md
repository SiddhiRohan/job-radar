# Changelog

## Unreleased

**A company scout.** More employers is the other way to more postings. Each morning the scout checks a few leads at
their careers sites, with the request the poll would make: employers you applied to or evaluated without following,
the H-1B sponsor lists and earlier searches in `companies/`, and, once a week, careers links and new employers
suggested by the model. A lead without a link is looked for on Greenhouse, Lever and Ashby under its name; a Workday
site is never guessed. Each find shows its open roles, how many match your titles and its H-1B record, and joins the
daily search only when you press Follow on the Agents view or run `python -m radar.scout follow "<name>"`. Also in
the chat ("find me more employers") and with `/radar-scout`.

**A weekly filter audit.** The title, seniority, domain and location rules drop most of what the searches return
before anything is scored. The radar now logs every drop for two weeks, and once a week an agent sends a sample of
the titles dropped most often, with postings skipped for sponsorship or years, to the model: it names the ones you
would probably have wanted and suggests the narrowest `config.json` change that would have kept them. Nothing
changes until you press Apply on the Agents view or run `python -m radar.agents audit apply N`. Also in the chat
("am I missing jobs?") and with `/radar-audit`.

**Interview debriefs.** Right after a screen or an interview, say how it went, in the chat, on the Agents view or
with `/radar-debrief`, and an agent writes what was asked with a stronger answer for each weak one, what the
interviewer seemed unsure about, what you said you would send, what to prepare next, and a thank-you note to send
yourself. Every round is kept, and the next prep for that role starts from what the debriefs found. Numbers stay to
what you said and your resume. From a terminal: `python -m radar.agents debrief "<company>" < account.txt`.

**Follow-ups, one employer at a time.** An employer with a follow-up draft waiting, or one written in the last two
weeks, gets no second draft for its other roles until then, so a recruiter never receives three notes in a week.
LinkedIn notes are asked for at 280 characters, leaving room under the limit, and the Follow-ups card folds each
draft to one line. The brief no longer announces the previous day's drafts again.

**Interview prep, written for you.** When an email moves an application to a screen or an interview, an agent writes
the prep that morning from the stored posting, its fit factor by factor, your resume and the employer's sponsorship
record: what they will probe, likely questions with what to answer from, stories from your resume, the gaps and an
honest way to answer them, questions to ask, and a plain answer to the sponsorship question. A number that is not in
the posting or your resume is replaced by [?] and named, never made up. Ask the chat ("prep me for my Contoso
interview"), use `/radar-prep`, or write one for any application on the new Agents view.

**Follow-up drafts.** For applications quiet for ten days whose posting the watcher still finds open, an agent
drafts a LinkedIn note under 300 characters, an email, and the LinkedIn search that finds the recruiter. Nothing is
sent: copy it, send it yourself, and mark it sent. Five a run at most, oldest first.

**Skill gaps and the sponsor map.** Two agents that only count, so they cost nothing: the skills a month of scored
postings found missing, with how many of those postings scored 3, one point below Apply, and the confirmed skills
your resume fails to show; and what each employer's own recent postings say about sponsorship, next to its default,
with the defaults its postings contradict. `python -m radar.gaps`, `python -m radar.sponsormap`.

**Agents, from anywhere.** The morning run writes the prep and drafts after the watcher (`python -m radar.agents
run`), the brief says what they wrote, and the Agents view, the chat and the terminal all read the same files.
Without an API key, `python -m radar.agents next` and `save` let a coding assistant write them, checked against the
same schema; `/radar-agents` runs the loop. Settings are under `agents` in `config.json`.

**Find an application.** A search at the top of Applied lists the applications whose company, role or status
matches what you type, word by word, with the matches highlighted and the status still changeable. Press `f` to
jump to it.

**Rejections in plain words.** The rejections card now opens with how every application turned out (good replies,
rejections, still waiting), names the clearest pattern in one sentence, and groups applications by role, level,
resume, fit score, years asked, sponsorship or company. Each group says whether it is rejected more or less often
than your average, or that it is too small to tell, and clicking it lists its applications.

**An intro video, and a README for going public.** The whole 47-second video plays at the top of the README as a
silent animation; the MP4 with sound is `docs/media/job-radar-intro.mp4`. The README now starts with why the radar
helps on a student visa and what a morning with it looks like, and adds what leaves your machine and a short FAQ.

**Score with a coding assistant, no API key needed.** `python -m radar.handscore next` writes the postings waiting
for a score, with the rules, the verdict schema, the resumes and the profile, to `.cache/to_score.json`; the
assistant judges them and `python -m radar.handscore save <file>` checks every verdict against the schema before
storing it, naming what is wrong with any it refuses. `/radar-score` runs the whole loop in Claude Code.

**Add an employer from a link.** `python -m companies.add "Name" <link>` takes a Workday careers site or posting,
or a Greenhouse, Lever or Ashby board, checks it with one request, and adds the employer to `companies.json`. A
coding assistant does the same with `/radar-add`, finding the link when it is not given. The chat in the web app
can now do both: paste a job link to have it judged, or ask it to add an employer.

**Email statuses for Greenhouse postings by id.** A Greenhouse posting is stored under the board's own number, which
emails never quote. The board also gives the employer's requisition id when there is one; it is now kept on the
posting, and an email quoting it moves the application as a Workday requisition id does.

**US cities that share a name with a city abroad are kept.** Vancouver, WA; Dublin, OH and CA; Vienna, VA;
Melbourne, FL; Warsaw, IN; and a few more were dropped by the US-only rule because the city name alone is on the
list of places abroad. The pairs are listed one by one: a bare state code would also keep "Bengaluru, IN" and
"Munich, DE", whose country codes are state codes too.

**Half-price scoring, if you can wait.** With `"score_batch": true` in `config.json` the run sends its postings
to Claude as one batch through the Message Batches API, at half the price. The run waits up to an hour, then asks
directly about anything the batch did not answer, so every posting under the cap still gets a score. Off by
default. `radar/batch.py`.

**Job-board postings watched and judged.** The posting watcher checks Greenhouse, Lever and Ashby postings by whether
the board still lists them, and `python -m radar.evaluate` takes a link from any of the three as well as Workday.

**Every morning, even with the app closed.** One switch on the Setup page, or `python -m radar.schedule install`,
asks the computer's own scheduler (Task Scheduler, launchd or cron) to start the run at `run_time`. The doctor says
which of the two ways is in use. A second copy of the radar on the same computer leaves the first one's task
alone.

**A morning brief.** The last step of each run writes a short note: the three postings to apply to first with one
line on why, status changes from email and postings that closed since the last brief, applications quiet for ten
days, and one pattern in the rejections. It sits at the top of Today, answers `python -m radar.brief`, and is a chat
tool. No model call.

**Runs itself every morning.** While the web app is open the radar runs at `run_time` each day, and catches up as
soon as the app opens if the computer was off. A lock makes sure the app, the operating system's scheduler and a
terminal never run it twice at once.

**A single resume is enough.** `Resume/resume.docx`, or an entry and an experienced file, works next to the original
folder tree; `profile.md` is optional.

**The fit, factor by factor.** Each newly scored posting carries four factors from Claude: experience (the same kind
of work at the depth asked, not shared keywords), level, skills and domain, each marked meets, partial or gap with
what the posting asks and what the resume shows. Sponsorship, location and pay are read by rule from the stored
posting. The posting drawer shows all seven above the description; Apply and Entry level rows in the digest add a
line such as `gaps: skills (Databricks), domain`. Postings scored earlier show nothing new. About 200 to 400 more
output tokens per scored posting. `radar/fit.py`, `radar/factors.py`. The drawer also no longer prints "null" above
a posting that has no fit note yet.

**Employers on Greenhouse, Lever and Ashby.** Eighteen employers that are not on Workday are polled through their
public job boards: Airbnb, Block, Chime, Coinbase, Databricks, Datadog, DoorDash, Dropbox, HubSpot, Lyft, MongoDB,
Okta, Robinhood, Stripe and Twilio on Greenhouse, Palantir and Spotify on Lever, Snowflake on Ashby. A board is read
whole in one request per run, and its postings go through the same title, date-window and US rules as Workday results,
with no second request for the description. Ashby pay comes from its compensation field, so those postings show a
range too. `radar/boards.py` and `radar/boardparse.py`; `python -m companies.board "Name" <URL>` adds another employer
from a careers, board or posting address. Mail sync, pasted Workday URLs and the companies report skip board entries
where they look for a Workday tenant, and a few more non-US places seen on Greenhouse (Serbia, Ukraine, EMEA and
others) count as non-US.

**Rejections move on their own by role.** A rejection email without a requisition id now moves the one application
whose role it names ("applying for the Data Engineer II position"); a rejection for a role not on the list is kept
apart on the Email card instead of waiting for review. `radar/rolematch.py`; `python -m radar.mail --recheck`
re-decides the emails already waiting.

**Posting drawer.** Click a row on Today, press Enter on the keyboard cursor, or pick a posting in the palette:
the stored description opens in a sheet on the right with the pay sentence and the sponsorship phrase highlighted,
the fit note on top, and Mark applied, Tailor and Open on Workday in the footer. `GET /api/posting`,
`salary.sentence()`. No new requests to Workday.

**Board, tiles, accents.** Cards drag between the Applied board's columns through the same status call, so Undo
works. Tile numbers count up when they enter view; rows, cards and tiles fade up as they scroll in where the browser
has scroll-driven animations. An accent picker in the header (teal, indigo, rust) remembered per browser and applied
before first paint.

**Command palette.** Ctrl+K (or the Search button) opens one box over the page: jump to a view, a digest day or
any posting on the page, or run the radar, check mail, check postings, start a chat thread. A query that matches
nothing goes to the assistant. `web/palette.js`, no server changes.

**Visual pass.** Sticky glass header with a blur and a rule that appears on scroll, pill navigation, conic score
rings that fill to the fit out of five, Instrument Sans for headings, company names and big numbers, two-stop
shadows on cards and tiles, a faint accent glow behind the top of the page. Dark mode has its own values.

**More postings per day.** Every tier is polled daily, tier 2 reads three pages and tier 3 two, "analytics" joins
the search terms, "Sr" no longer removes a title (Senior never did, and both score 4 at the same rate), and the
score cap rises to 120. The run grows from about half an hour to about an hour.

**Undo, keyboard, chips, motion.** A mistaken Mark applied, status change or settled email can be taken back from
the toast. Keyboard shortcuts on Today (`?` lists them). Filter chips: hide applied, pay listed, score 4, entry
level, and the day's busiest companies. Rows ease in and settle, views cross-fade, all off under reduced motion.

**Postings since you applied.** `radar/watch.py` re-reads the posting behind every open application once a day
(after the mail step) and records when it closed, was retitled, repriced or rewritten. Closed with no reply is
shown as the quiet rejection it usually is. A card on Applied with a "Check postings" button, `/api/watch`, and a
`posting_status` chat tool.

**What the rejections say.** `radar/patterns.py` joins applications with the stored postings and shows where
rejections cluster (title family, seniority wording, resume base, fit score, years asked, sponsorship default,
company) against the overall rate. Counts only, with a three-rejection floor. A card on Applied and a chat tool.

**Brand.** A 3D logo (Higgsfield, GPT Image 2.5), a six-second ident video (Seedance 2.5), PNG favicons and a
social preview card. The header and README use the logo; the README opens with the ident loop.

**Personal details out of the code and docs.** Name, resume file name and personal stopwords move to `.env`
(`radar/owner.py`); the resume folder map and date-overlap notes move to the ignored `Resume/` folder; docs speak
of the owner.

**Missed rejections.** Six more rejection wordings, found by scanning real hiring emails ("decided not to move
forward" among them); review guesses come from the sender and subject before the body.

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
