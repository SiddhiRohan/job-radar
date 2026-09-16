# Job radar

A personal job sourcer for Workday career sites. Every morning it polls about 110 companies, keeps the
Data Engineer, Data Scientist, ML Engineer and AI Engineer postings that fit an entry-to-mid profile,
scores each one against two resume bases, and writes a shortlist. A small web UI shows the shortlist,
tracks applications, and carries a chat assistant that can run the radar, mark rows applied, and
tailor a resume for one posting on request.

It is built for one person and one visa situation (F-1 OPT, needs H-1B), so the filters are opinionated:
postings that say "no sponsorship", ask for six or more years, or sit outside the US are dropped before
scoring.

## How it works

1. `radar.poll` calls each company's Workday JSON endpoint with four search terms, pages through the
   results, and fetches the detail JSON for every new posting. It reads years required, sponsorship
   language, contract wording, and the real country from the detail, and applies the title and
   seniority rules from `config.json`.
2. `radar.score` sends the survivors to Claude with the profile and both resume outlines and gets back a
   strict JSON verdict: fit 1 to 5, which base resume to use, one reason, one gap.
3. `radar.digest` writes `digests/<date>.md` with Apply, Maybe, Contract, and Everything else sections
   and updates `last_run.json`.
4. `server.py` serves `web/` and reads what the run wrote. It never polls on its own.

Companies live in `companies.json` with the tenant, shard, site, a tier that sets how many pages to
fetch, and a default for whether the company sponsors. The tooling that found and verified those
entries is in `companies/`.

## Run it

Daily pipeline, also what the 7:30 AM scheduled task runs:

    python run.py

Wider window when the shortlist is thin:

    python run.py --days 3 --all-tiers

The UI:

    python server.py

Then open http://localhost:8000. Views: Today (ranked shortlist), Tailor (side-by-side resume editor for
one posting, or paste any Workday job URL), Applied (what you sent, with status). The Chat button opens
the assistant; threads are kept on disk.

Tailor a resume from the command line:

    python -m tailoring.apply <company> <req_id> --cover

## Setup

- Python 3.11, `pip install -r requirements.txt`.
- `ANTHROPIC_API_KEY` in the environment or in `.env`.
- Base resumes under `Resume/` at the paths named in `tailoring/resumes.py`.
- `profile.md` (who you are, what you want) and `skills_confirmed.md` (skills the tailoring step is
  allowed to name). Both are personal and ignored by git; `docs/RESUME_RULES.md` explains the format.

## Layout

| Path | What is there |
| --- | --- |
| `run.py`, `radar/` | poll, score, digest, prepare, the Workday client, filters, the chat assistant |
| `tailoring/` | plan, apply, finalize, cover letters, skill vocabulary |
| `companies/` | verify, resolve, expand, and the candidate ledger behind `companies.json` |
| `server.py`, `web/` | FastAPI server and the vanilla HTML, CSS, and JS UI |
| `tests/` | offline tests for the URL parser, years gate, and sponsorship tagging |
| `docs/` | STATUS, DECISIONS, CHANGELOG, UI_NOTES, COMPANIES_REPORT, RESUME_MAP, RESUME_RULES |

## Working on it

Branch from `main`, open a PR, let CI run ruff and pytest, squash-merge. Pre-commit runs ruff, a secrets
scan, and whitespace fixes. Details and the rules for new code are in `CLAUDE.md`; the reasoning behind
the bigger choices is in `docs/DECISIONS.md`.
