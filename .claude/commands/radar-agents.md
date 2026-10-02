---
description: Run the agents: interview prep, follow-up drafts, skill gaps and the sponsor map
argument-hint: [prep | followups]
---
Run the agents and say what they found.

1. Run `python -m radar.agents run $ARGUMENTS`. With an API key it writes interview prep for applications at a
   screen or interview, and follow-up drafts for applications quiet for ten days whose posting is still up.
2. If it says there is no API key, do the writing yourself. Run `python -m radar.agents next $ARGUMENTS`, read
   `.cache/agent_tasks.json`, and answer each task as its agent's rules say, from the task's input alone, following
   that agent's schema. Never add a number the input does not contain. Write one JSON object, `{"<task id>": answer}`,
   to `.cache/agent_answers.json`, then run `python -m radar.agents save .cache/agent_answers.json`. If it names an
   answer it did not store, fix that one and save again.
3. Run `python -m radar.gaps` and `python -m radar.sponsormap`.
4. Report in a few lines: preps ready (`python -m radar.agents show prep`), follow-up drafts waiting
   (`python -m radar.agents show followups`), the top three skill gaps, and any employer default the sponsor map asks
   them to check. Drafts are theirs to send; never send one.

The task file holds their resume and profile: keep it on this machine and do not paste it anywhere else.
