# Contributing

Thanks for helping. Job radar is small on purpose: plain Python, a local web app, and files a person can read. These
rules keep it that way.

## Set up

```bash
pip install -r requirements-dev.txt
pre-commit install
```

Tests are offline and fast: `python -m pytest -q`. Run `pre-commit run --all-files` before opening a PR.

## How the code is written

- Python 3.11+, `requests` plus the standard library where possible. A new dependency needs a reason in the PR.
- Files stay under about 150 lines. When one grows past that, split it.
- One request to an employer's site at a time, with a 1.5 second gap. JSON endpoints only; never scrape HTML.
- The web app (`server.py`, `web/`) calls the pipeline modules and adds no logic of its own. Anything the app can
  do should also work from a terminal command.
- Add a test for anything that broke once.

## Git

- Branch from `main` (`feature/<name>`, `fix/<name>`, `chore/<name>`), open a PR, let CI pass, squash-merge.
- Never stack PRs. Every PR is based on `main`; if a change needs another PR first, wait for that one to merge.
- One change per commit. Message: `area: what changed`, imperative, under 60 characters. The body says why, not
  what. Examples: `sponsor: treat "no visa sponsorship" as no`, `ui: minimize chat to a pill`.
- No attribution trailers in commits or PR text.

## Personal data never enters git

Everything about the person using the radar stays on their machine: `Resume/`, `profile.md`, `skills_confirmed.md`,
`memory.md`, `applications.md`, `.env`, `jobs.jsonl`, `seen.json`, `last_run.json`, `digests/`, `.cache/`, `logs/`,
`notes/`. All of them are in `.gitignore`. If one shows up in `git status`, fix `.gitignore`; never commit it.

The privacy guard in the pre-commit hooks backs this up. Put your own name, email addresses, employers and school in
`.privacy-terms` (one per line, ignored by git). The guard also reads your name and email from `.env` and your
requisition ids from `applications.md`, and blocks any commit that contains one of them. Before a PR, check its text
too: `python scripts/privacy_guard.py --text < pr-body.md`. Tests and docs use fictional employers such as Contoso
and Northwind.

## Where things live

- `start.py`, `run.py`, `server.py` at the root are the entry points; `config.json` and `companies.json` are the two
  files people edit.
- `radar/`: the daily pipeline (wd and boards, poll, filters, sponsor, store, score and batch, digest, prepare,
  mail, watch, agents, brief) plus `llm`, `fit`, `factors`, `chat`, `salary`, `mailmatch`, `rolematch`,
  `applications`, `evaluate`, `doctor`, `firstrun`, `autorun`, `schedule`, `runlock`. The agents are `prep`,
  `followup`, `gaps` and `sponsormap`, with `facts` (the number lock), `agentview` (plain pages) and `agentchat`
  (their chat tools).
- `tailoring/`: apply, plan, tailor, letters, finalize, skills, resumes, skills_extract.
- `companies/`: finding and verifying employers, with their data files; `add` adds one from a link.
- `web/` the UI, `tests/` pytest, `scripts/` the privacy guard, `.claude/commands/` the assistant commands,
  `docs/` configuration, decisions, status and changelog.
- Modules import each other as `from radar import wd`; run everything from the repo root.

## Things worth knowing

- Workday: `total` is only on the first page of a search (0 after). Tenant roots return 406 for valid and invalid
  tenants alike, so tenant slugs come only from URLs actually seen. A taken-down posting answers 403 with Workday's
  JSON error body.
- Greenhouse, Lever and Ashby: one request returns a board's every posting with its description, so a board costs
  one request a run. A posting's id there is the board's own; Greenhouse also gives the employer's requisition id.
- Sponsorship is decided per posting from its wording (`radar/sponsor.py`) plus the employer's default; the model's
  own "no" also sends a posting to Skipped.
- Tailoring may use only words from the base resume and `skills_confirmed.md`. Numbers, dates, titles and employers
  are locked. A rewrite that adds anything else turns into a question in notes.md (`docs/RESUME_RULES.md`).

## Docs

Record judgment calls in `docs/DECISIONS.md`, user-visible changes in `docs/CHANGELOG.md`, and keep
`docs/STATUS.md` current at the end of a round of work. `docs/CONFIG.md` explains every setting and must change with
the code.
