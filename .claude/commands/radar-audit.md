---
description: Check whether the filters are throwing away jobs you would want
---
Run the filter audit and help them decide what to change.

1. Run `python -m radar.agents audit`. It samples what the title, seniority, domain and location rules dropped since
   the last audit, plus postings skipped for sponsorship or years, and writes which ones they would probably have
   wanted and the config.json changes that would have kept them. Without an API key, run
   `python -m radar.agents next audit`, answer the task in `.cache/agent_tasks.json` yourself as its rules say, put
   the answer in `.cache/agent_answers.json`, and run `python -m radar.agents save .cache/agent_answers.json`.
2. Show the postings worth seeing, then each suggested change as a before and after of that setting in config.json.
3. Make a change only after they agree, with `python -m radar.agents audit apply N`. Say the next run will use it.
