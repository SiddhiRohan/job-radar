---
description: Score new postings yourself, with no API key
argument-hint: [how many, 10 by default]
---
Score the postings that are waiting, using your own judgment instead of the Anthropic API.

1. Run `python -m radar.handscore next $ARGUMENTS`. It writes `.cache/to_score.json`: how to answer, the rules, the
   verdict schema, their profile and both resume bases, and the postings in the order a run would score them.
2. Read that file and judge each posting exactly as the rules say, against both resumes. Judge the work the role
   needs, not shared keywords, and keep every quote short. Write one JSON object to `.cache/verdicts.json`,
   `{"<id>": verdict}`, each verdict following the schema, four factors first.
3. Run `python -m radar.handscore save .cache/verdicts.json`. If it names a verdict it did not store, fix that one
   and save again.
4. Run `python -m radar.digest`, then lead with the postings that scored 4 or 5, as `/radar-today` does.

The file holds their resume and profile: keep it on this machine and do not paste it anywhere else.
