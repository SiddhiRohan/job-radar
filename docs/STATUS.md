# STATUS

## Current state (2026-09-27)

Job radar runs every morning on one machine for one person: it polls employer career sites, keeps the postings
that fit the configured roles, scores them against the user's resume, and serves a local web app for the shortlist,
tailoring and tracking. The dated history of the author's own runs is kept in a private notes folder, not here.

**What works**

- Sourcing from 180 employers: 162 verified Workday sites, polled with a 1.5 s gap between requests, and 18 on
  Greenhouse, Lever and Ashby boards, read whole in one request each. Title, seniority, domain, US-location,
  years-asked and sponsorship rules run before any model call.
- Scoring against the resume with the Anthropic Messages API, prompt-cached. Each verdict carries the fit factor by
  factor: experience, level, skills and domain from the model, with what the posting asks and what the resume
  shows; sponsorship, location and pay by rule. Optional batch scoring at half the price.
- A morning brief at the end of each run: what to apply to first and why, what changed, what went quiet.
- A local web app: Today with the brief, filter chips, keyboard shortcuts, a posting drawer and a command palette;
  Tailor with locked facts; Applied with a drag board, charts, email statuses, rejection patterns and posting
  changes; a Setup page for the resume, API key, profile and daily schedule.
- Setup in minutes: `start.bat`, `start.sh` or `start.command` makes the environment and opens the Setup page; a
  doctor names anything missing; one resume file is enough.
- Runs itself every morning while the app is open, or through the computer's own scheduler when it is closed; a
  lock keeps two runs from overlapping.
- A command-line workflow for coding assistants: `CLAUDE.md`, `AGENTS.md`, slash commands in `.claude/commands/`,
  and terminal commands to evaluate a link, record an application, read the brief and check the setup.
- Email statuses over read-only IMAP: automatic with a requisition id, and for rejections that name the role of
  exactly one application; everything else waits for review.
- A daily watcher for the postings behind open applications, on Workday and on the three boards.
- A chat assistant with tools over the shortlist, tailoring, email, posting status and the brief.
- The server accepts changes only from its own pages. A pre-commit check keeps personal details out of commits.
- 340 offline tests, CI on every PR, pre-commit with ruff and gitleaks.

**Next**

- Record H-1B filings for the six board employers with no sponsorship data, so recomputing tiers keeps them in
  tier 2.
- Keep Greenhouse requisition ids, so email statuses can match board postings by id.

**Known gaps**

- US postings only. One user per install. Tailoring needs a Word resume; a text resume scores but does not tailor.
- Email statuses read Gmail only.
