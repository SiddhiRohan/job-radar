# STATUS

## Current state (2026-10-01)

Job radar runs every morning on one machine for one person: it polls employer career sites, keeps the postings
that fit the configured roles, scores them against the user's resume, and serves a local web app for the shortlist,
tailoring and tracking. The dated history of the author's own runs is kept in a private notes folder, not here.

**What works**

- Sourcing from 180 employers: 162 verified Workday sites, polled with a 1.5 s gap between requests, and 18 on
  Greenhouse, Lever and Ashby boards, read whole in one request each. Title, seniority, domain, US-location,
  years-asked and sponsorship rules run before any model call.
- Scoring against the resume with the Anthropic Messages API, prompt-cached. Each verdict carries the fit factor by
  factor: experience, level, skills and domain from the model, with what the posting asks and what the resume
  shows; sponsorship, location and pay by rule. Optional batch scoring at half the price, or scoring by a coding
  assistant with no API key.
- A morning brief at the end of each run: what to apply to first and why, what changed, what went quiet.
- A local web app: Today with the brief, filter chips, keyboard shortcuts, a posting drawer and a command palette;
  Tailor with locked facts; Applied with search, a drag board, charts, email statuses, rejection patterns in
  plain words and posting changes; a Setup page for the resume, API key, profile and daily schedule.
- Setup in minutes: `start.bat`, `start.sh` or `start.command` makes the environment and opens the Setup page; a
  doctor names anything missing; one resume file is enough.
- Runs itself every morning while the app is open, or through the computer's own scheduler when it is closed; a
  lock keeps two runs from overlapping.
- A command-line workflow for coding assistants: `CLAUDE.md`, `AGENTS.md`, slash commands in `.claude/commands/`,
  and terminal commands to evaluate a link, add an employer from a link, record an application, read the brief,
  score without a key and check the setup.
- Email statuses over read-only IMAP: automatic with a requisition id, and for rejections that name the role of
  exactly one application; everything else waits for review.
- A daily watcher for the postings behind open applications, on Workday and on the three boards.
- Four agents after each run: interview prep when an email brings a screen or an interview, follow-up drafts for
  quiet applications whose posting is still up, skill gaps across a month of verdicts, and a sponsor map of what
  each employer's own postings say. The first two write with the API or a coding assistant, with numbers held to
  the posting and the resume; the other two only count. They show on an Agents view, in the brief, in the chat and
  in the terminal.
- A chat assistant with tools over the shortlist, tailoring, email, posting status, the brief and the agents; it
  judges a pasted job link and adds an employer from a link too.
- The server accepts changes only from its own pages. A pre-commit check keeps personal details out of commits.
- 456 offline tests, CI on every PR, pre-commit with ruff and gitleaks.

**Next**

- Record H-1B filings for the six board employers with no sponsorship data, so recomputing tiers keeps them in
  tier 2.
- An interview debrief: notes typed into the chat after an interview become what was asked, what to improve and a
  thank-you draft, and feed the next round's prep.
- A filter auditor: a weekly look, with the model, at titles the seniority and domain rules removed, to find the
  postings worth getting back.

**Known gaps**

- US postings only. One user per install. Tailoring needs a Word resume; a text resume scores but does not tailor.
- Email statuses read Gmail only.
