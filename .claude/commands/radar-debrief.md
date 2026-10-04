---
description: Debrief a screen or an interview, and practise the weak answers
argument-hint: <company> [req_id]
---
Debrief their screen or interview at $ARGUMENTS.

1. If they have not said how it went, ask in one message: what they asked, how they answered, anything the
   interviewer seemed unsure about, names, and anything they promised to send.
2. Put their account, in their own words, in `.cache/debrief_account.txt` and run
   `python -m radar.agents debrief "<company>" [req_id] < .cache/debrief_account.txt`. It keeps the account and, with
   an API key, writes the debrief. Without a key, run `python -m radar.agents next debrief`, answer the task in
   `.cache/agent_tasks.json` yourself as its rules say, put the answer in `.cache/agent_answers.json`, and run
   `python -m radar.agents save .cache/agent_answers.json`.
3. Show it with `python -m radar.agents show debrief "<company>"`: lead with the weak answers and their stronger
   versions, then what they owe, then the thank-you note to send today. If the application is still at applied, offer
   `python -m radar.applications status "<company>" <req_id> screen` (or interview).
4. Offer a practice round: ask the weak questions one at a time, wait for each answer, and give short feedback that
   points back to their resume. The next prep for this role reads the debrief.

Never send the thank-you note for them. Their account and resume stay on this machine.
