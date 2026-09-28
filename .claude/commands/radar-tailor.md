---
description: Tailor the resume for one posting
argument-hint: <company> <req_id>
---
Run `python -m tailoring.apply $ARGUMENTS --no-prompt --yes` (quote the company name if it has spaces). It writes
a draft to review, never sends anything. Report the folder it wrote, the resume it produced, and every question in
its notes.md. If it stops because the fit assessment says skip, tell them why and ask before rerunning with
`--force`. Tailoring follows `docs/RESUME_RULES.md`:
numbers, dates, titles and employers stay as they are, and nothing the resume does not already show is added.
Ask the person about each question rather than guessing.
