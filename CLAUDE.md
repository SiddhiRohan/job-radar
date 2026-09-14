# Working rules for this repo

Personal job radar: polls Workday career sites, scores postings against two resume bases, tailors resumes,
and serves a small web UI. Plain Python 3.11+, `requests` plus the standard library where possible, files
under about 150 lines, one request to Workday at a time with a 1.5 s gap, JSON endpoints only, never HTML scraping.

## Git

- Never commit to `main` directly. Branch from `main` (`feature/<name>`, `fix/<name>`, `chore/<name>`), open a
  PR, let CI pass, and squash-merge. Rohan merges.
- One change per commit. Commit message: `area: what changed`, imperative, under 60 characters. The body says
  why, not what. Examples: `sponsor: treat "no visa sponsorship" as no`, `ui: minimize chat to a pill`.
- No attribution trailers of any kind (no Co-Authored-By, no tool names) in commits or PR text.
- Never push without confirming the remote is private first: `gh repo view --json isPrivate`.
- Pre-commit runs ruff (lint and format), gitleaks, end-of-file-fixer, trailing-whitespace. Run
  `python -m pre_commit run --all-files` before opening a PR.
- Tests are offline and fast: `python -m pytest -q`. Add a test for anything that broke once.

## Personal files: ignored, never re-add

These hold Rohan's data and must stay out of git even if they appear in the working tree:
`Resume/`, `profile.md`, `skills_confirmed.md`, `memory.md`, `applications.md`, `.env`,
`jobs.jsonl`, `seen.json`, `last_run.json`, `digests/`, `.cache/`, `logs/`, `*.log`, and the root
`Resume - *.docx` / `.pdf`. If one shows up in `git status`, fix `.gitignore`, do not commit it.

## Conventions worth knowing

- Workday quirks: `total` is only on the first page (0 after); Salesforce search is keyword-OR and date-sorted;
  tenant roots return 406 for valid and invalid tenants alike, so slugs come only from URLs actually seen.
- Sponsorship sections use the regex tag in `sponsor.py` plus the company default; the model's own "no" also
  sends a posting to Skipped.
- Tailoring vocabulary is the base resume text plus `skills_confirmed.md`. Numbers, dates, titles, and employers
  are locked. Rewrites that add anything outside that vocabulary are reverted into a question in notes.md.
- The UI (`server.py`, `web/`) imports the pipeline modules and adds no logic of its own.
- Record unattended judgment calls in DECISIONS.md; keep STATUS.md current at the end of a round.
