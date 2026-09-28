---
description: Add an employer to the daily search
argument-hint: <employer> [link to its jobs]
---
They want to add: $ARGUMENTS

1. If they gave no link, find one to the employer's jobs: its Workday careers site or any posting on it
   (`<tenant>.wd<N>.myworkdayjobs.com/...`), or its board on Greenhouse (`job-boards.greenhouse.io/<board>`),
   Lever (`jobs.lever.co/<board>`) or Ashby (`jobs.ashbyhq.com/<board>`). An employer's own careers page usually
   leads to one of these from any job on it.
2. Run `python -m companies.add "<Employer>" <link>`. It checks the link with one request and adds the employer to
   `companies.json`; running it again updates the entry.
3. Say how many open postings it found and that the next run includes it. If the link is not one the radar reads,
   the employer uses another hiring system, which the radar does not read yet; say so plainly.
