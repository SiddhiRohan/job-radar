---
description: Find more employers worth adding to the daily search
---
Run the company scout and help them choose employers to follow.

1. Run `python -m radar.scout`. It checks the next few leads at their careers sites: employers they applied to or
   evaluated without following, the H-1B sponsor lists, and the model's weekly suggestions.
2. When the model's leads are due, once a week, `python -m radar.agents run scout` asks it for careers links and new
   employers. Without an API key, run `python -m radar.agents next scout`, answer the task in
   `.cache/agent_tasks.json` yourself as its rules say, never making up a link, put the answer in
   `.cache/agent_answers.json`, and run `python -m radar.agents save .cache/agent_answers.json`; then
   `python -m radar.scout` checks the links.
3. Show what it found (`python -m radar.scout show`): open roles, roles matching their titles, the H-1B record.
4. Follow an employer only when they say so, with `python -m radar.scout follow "<name>"`, or skip one with
   `python -m radar.scout skip "<name>"`. The next run searches a followed employer.
