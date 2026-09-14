# UI notes

## Design plan (written before any code)

**Color** (5 named values plus one wash)

| Name | Hex | Use |
|---|---|---|
| Stone | #F1F2EE | page base, a cool pale gray-green paper, not cream |
| Ink | #171A1D | text |
| Ash | #5C6369 | secondary meta, rules |
| Teal | #0E5A4D | the single primary action on each screen |
| Apply green | #1E7A56 | Apply status, a signal not an alarm |
| Maybe ochre | #8C6B1A | Maybe status |
| Skip slate | #7A7F84 | Skip / applied-done state |
| Change wash | #D9EBE4 | background tint for changed words on Tailor |

**Type.** One family: Hanken Grotesk (Google Fonts), 400/500/600, with `font-feature-settings: "tnum"` so
scores and dates align. Reason: it is a quiet grotesk most people skip for Inter, and its slightly narrow
figures stack cleanly in a ranked column without shouting. Fallback: system-ui.

**Layout.** One left-aligned column (max 1100px, prose under 72ch): Today reads as a ranked ledger of rows,
Tailor as a proof page with the base copy on the left and the marked-up copy on the right.

Today:

    Today  Tailor  Applied                              2026-09-13 [<] [>]
    Polled 113 companies, kept 242, removed 874 by rule (522 seniority).
    Apply
    4   Adobe        Machine Learning Engineer        San Jose   2 days
        E3 / X4  experienced, two-page   likely   [Tailor] [Mark applied] [open]
    4   Workday      Machine Learning Engineer        Pleasanton 2 days
        ...
    Maybe
    (none)
    Contract
    Everything else (127)  v

Tailor:

    [paste a Workday job URL                      ] [Load]
    Adobe  Machine Learning Engineer  R171718
    Fit E3 / X4 (experienced, two-page)  likely: "no phrase found"  3+ years
    Platform tools missing: Databricks              cover letter: not required
    JD asks for: [ ] Databricks  [ ] Kubernetes
    Summary
    base text ..................... | tailored text with [changed words] .....
    Job 0  University of Maryland (ENST)
    bullet ........................ | bullet (moved) ..........  note: hard to defend
    Skills  |  Coursework
    [Rebuild resume]  Save to folder  Mark applied

**The one memorable element.** On Today the score is set at 28px in tabular figures at the left edge of
each row, so the column of numbers reads as a ranked list before any title is read. On Tailor the changed
words carry the teal wash with a 1px darker lower edge, easing in over 400 ms when the plan lands; it is
the only motion on the site.

## Review against the known defaults

- Cream + serif display + terracotta: not used. Stone base, one grotesk, teal accent.
- Near-black with acid green: not used.
- Broadsheet hairline columns: not used. One rule above each section, whitespace between rows.
- Identical rounded cards with shadow and gradient: not used. Rows, no cards, no shadows.
- All-caps tracked eyebrow labels: **changed.** The first wireframe had "APPLY" section labels; they are
  sentence case now.
- Meta strings joined with middle dots: **changed.** The first draft wrote "experienced · two-page";
  it is "experienced, two-page" now, and other meta is separated by spacing.
- Monospace for small data labels: **changed.** Req IDs and dates were going to be monospace; they use the
  same family with tabular figures instead.
- Arrows appended to button text: not used.
- Stat grid hero: not used. Header stats are one sentence.

## What was built

- `server.py` (FastAPI, 307 lines) wraps poll, score, plan, tailor, letters, finalize, skills, digest. Long work
  (plan, rebuild, cover letter, pasted-URL fetch and score) runs in a thread behind `/jobs/<id>`.
- `web/index.html`, `web/app.js`, `web/app.css`: vanilla, no build step. Total across the four files: 641 lines.
- `digest.py` gained `sections()` so the UI and the markdown digest split postings with the same rules.
- `python server.py` opens the browser; README.md has the one command.

## Screenshot critiques

- Today: the ranked score column works; the eye reads 4, 4, 4, 4 before any title. Removed one thing: the
  full "why" paragraph made each row four or five lines tall. It is now one clamped line that expands on hover.
- Tailor: the pane could not draw a screenshot in this session (rendering timed out), so it was verified through
  the DOM: verdict strip, 4 JD-skill checkboxes, 33 editable cells, 142 changed-word spans, 20 moved markers,
  8 inline notes, 4 action buttons, no console errors. Removed one thing: the base column showed raw `**`
  markers; it now renders them as bold like the tailored column.
- Applied: one row, status select with the five values, folder opens through `/api/open`.

## End-to-end run on the Adobe posting

Today -> Tailor (plan in about 40 s) -> one bullet edited -> Rebuild (finalize humanized 14 of 38 paragraphs,
properties cleared) -> download served (30.8 KB) -> Save to folder into a scratch path. The existing
`Resume/For Adobe/R171718_Machine-Learning-Engineer/` was not touched. The test `applications.md` row was
removed afterwards; the file is gitignored.

## What I would change next

- Pasted-URL ingest gives the posting `posted_on: "pasted"` and a fixed `search_term`; fine for Tailor, but it
  will show on Today under that day's date. A "pasted" section or a filter would be cleaner.
- Changed-word highlighting is a word LCS; when the model rewrites a whole bullet nearly every word lights up,
  which is honest but noisy. A sentence-level pass first, then words inside changed sentences, would read better.
- Contenteditable cells re-render on blur, so bold toggling while typing is not supported; a small toolbar or
  Ctrl+B mapping to the `**` convention is the obvious addition.
- Outreach text is generated by `apply.py --outreach` only; the UI does not offer it yet.
- The "why" line on Today could hide entirely for rows already marked applied.
- `/api/today` groups by `first_seen` date, so two runs on the same day merge into one list. That matched the
  digest today, but a run-id filter would keep them apart.

## Chat assistant (added 2026-09-14)

A drawer on the right ("Chat" in the header) with a tool-using assistant. It sees the current view, the Today rows,
and the open Tailor state, and acts with tools: navigate, refresh, run_radar (poll, score, digest, prepare in the
background; the Today button "Run the radar" does the same), run_status, mark_applied, set_status, open_tailor,
edit_section (lands as a highlighted change in the editor), rebuild. Server-side tools run in `chat.py`; page tools
come back as actions the browser executes after the reply. Threads are per browser session, in memory, trimmed to
40 turns. Each message is one or more Sonnet calls.
