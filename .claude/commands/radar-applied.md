---
description: Record an application or a reply
argument-hint: <company> <req_id> [title | status]
---
Record what they tell you with `python -m radar.applications`:
- applied: `add "<company>" <req_id> "<title>"`
- a reply: `status "<company>" <req_id> <applied|screen|interview|rejected|offer>`
- the list: `list`, or `list interview`
Use $ARGUMENTS for the company and id when given, and ask for anything missing.
