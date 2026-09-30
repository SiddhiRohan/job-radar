---
description: Run the radar now
---
Run `python run.py` from the repository root. It polls every employer, scores new postings, writes today's digest,
then checks email and the postings behind open applications. It can take up to an hour. Only one run happens at a
time: if one is already going, it says so and stops, which is fine. When it finishes, summarise with `/radar-today`.
