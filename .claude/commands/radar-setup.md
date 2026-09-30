---
description: Check the setup and learn what jobs to look for
---
Set up job radar for the person using it, following "Start every session by checking the setup" and "The first time"
in CLAUDE.md.

1. Run `python -m radar.doctor` and help with each FIX line. Never ask for the API key in chat; they put it in `.env`.
2. If `profile.md` is missing or thin, ask in one message: roles, level, where they can work, visa sponsorship needed,
   pay floor, and what they never want to see. Write `profile.md` from the answers.
3. Propose `config.json` changes that match (search terms, title patterns, exclusions), as a before and after. Apply
   them only after they agree.
4. Offer the first run with `python run.py`, and say it can take up to an hour.
