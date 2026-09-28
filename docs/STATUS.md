# STATUS

## Current state (2026-09-27)

Job radar runs every morning on one machine for one person: it polls employer career sites, keeps the postings
that fit the configured roles, scores them against the user's resume, and serves a local web app for the shortlist,
tailoring and tracking. The dated history of the author's own runs is kept in a private notes folder, not here.

**What works**

- Sourcing from 162 verified Workday employers, tiered, polled daily with a 1.5 s gap between requests. Title,
  seniority, domain, US-location, years-asked and sponsorship rules run before any model call.
- Scoring against two resume bases (entry and experienced) with the Anthropic Messages API, prompt-cached; Apply,
  Entry level, Maybe and Contract sections; pay extracted from the posting text.
- A local web app: Today with filter chips, keyboard shortcuts, a posting drawer and a command palette; Tailor with
  locked facts; Applied with a drag board, charts, email statuses, rejection patterns and posting changes.
- Email statuses over read-only IMAP: automatic with a requisition id, and for rejections that name the role of
  exactly one application; everything else waits for review.
- A daily watcher for postings behind open applications (closed, retitled, repriced, rewritten).
- A chat assistant with tools over the shortlist, tailoring, email and posting status.
- 164 offline tests, CI on every PR, pre-commit with ruff and gitleaks.

**In progress**

- Greenhouse, Lever and Ashby job boards next to Workday.
- A fit explained factor by factor, with evidence from the posting and the resume.
- A setup that takes minutes: start scripts, a first-run page, self-scheduling, and a command-line workflow for
  coding assistants.

**Known gaps**

- US postings only. One user per install. The resume layout still assumes two bases.
