---
description: Interview prep for one application
argument-hint: <company> [req_id]
---
Get them ready for a screen or an interview at $ARGUMENTS.

1. Run `python -m radar.agents show prep "<company>"`. If there is a prep for this application and stage, use it.
2. Otherwise run `python -m radar.agents run prep --for "<company>" [req_id]`. Without an API key, run
   `python -m radar.agents next prep --for "<company>" [req_id]`, write the answer to the one task in
   `.cache/agent_tasks.json` yourself as its rules say, and store it with `python -m radar.agents save <file>`.
3. Lead with the likely questions and the stories from their resume, then the gaps and how to answer them, then the
   work authorization answer. Offer a practice round: ask one question at a time, wait for their answer, and give
   short feedback that points back to their resume.

Use only what the resume and the posting say. The work authorization part is guidance, not legal advice.
