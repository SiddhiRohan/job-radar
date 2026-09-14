# Job radar

Personal Workday job radar: polls company career sites, scores postings against two resume bases, and
gives a morning shortlist with one-click tailoring.

## Run it

    python server.py

Opens http://localhost:8000 in the browser. Three views: Today (the shortlist), Tailor (edit and rebuild a
resume for one posting, or paste any Workday job URL), Applied (what you sent, with status).

The daily poll, score, and digest run from `python run.py` (scheduled at 7:30 AM). The UI reads what
that run wrote (`jobs.jsonl`, `last_run.json`) and never re-polls on its own.

## Files

- `run.py`, `radar/`: the daily pipeline (poll, score, digest, prepare).
- `tailoring/`: resume tailoring; `python -m tailoring.apply <company> <req_id>` from the command line.
- `companies/`: the tooling and data behind `companies.json`.
- `server.py`, `web/`: the UI; it imports the modules above and adds no logic of its own.
- `docs/`: STATUS, DECISIONS, UI_NOTES, COMPANIES_REPORT, RESUME_MAP, RESUME_RULES, CHANGELOG.
