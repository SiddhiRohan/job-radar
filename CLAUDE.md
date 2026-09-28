# Job radar: guide for coding assistants

You are helping one person run their own job search with this repository. It finds new postings at the employers
in `companies.json` every morning, keeps the ones that fit their roles, scores each against their resume, tracks
their applications, and reads replies from their email. Everything runs on their machine. Their files are private:
treat them that way.

If you are asked to change the code itself, read `CONTRIBUTING.md` first and follow it.

## Start every session by checking the setup

Run `python -m radar.doctor`. For each line marked FIX:

- **No resume found**: ask them to put their resume in `Resume/` as `resume.docx`. From Google Docs or Pages, save
  or download it as Word. If they point you at a file, copy it there. Two files named `entry...` and `experienced...`
  also work.
- **No Anthropic API key**: ask them to open `.env` and set `ANTHROPIC_API_KEY=` themselves; keys come from
  console.anthropic.com. Never ask them to paste a key into the chat, and never print `.env`.
- **Packages missing**: run `python start.py` once, or `pip install -r requirements.txt`.

## The first time: learn what they want

Ask in one short message: the roles they want, their level (new grad, 2 to 4 years, senior), where they can work,
whether they need visa sponsorship, a pay floor, and anything they never want to see. Then:

1. Write `profile.md` in their words: target roles, strongest experience, tools they do not have. Five to ten lines.
2. Propose changes to `config.json` so the search matches: `search_terms`, `title_patterns`,
   `entry_title_patterns`, `exclude_seniority`, `exclude_domain`, `us_only`. `docs/CONFIG.md` explains each key.
   Show the change as a before and after, and write it only after they agree.
3. Offer a first run: `python run.py` (see below).

## Everyday requests

| They say | Command | Do this |
| --- | --- | --- |
| What's new today? | `/radar-today` | `python -m radar.brief` gives the three to apply to first, what changed and what went quiet. The newest file in `digests/` has the full list. Lead with the brief. |
| Run it now | `/radar-run` | `python run.py`. It can take up to an hour; only one run happens at a time, so a second start just says so. |
| Is this job right for me? | `/radar-evaluate <link>` | `python -m radar.evaluate <link>` for a Workday, Greenhouse, Lever or Ashby posting, or `<company> <req_id>` for one already stored. Explain the verdict plainly, including gaps. |
| Tailor my resume for it | `/radar-tailor <company> <req_id>` | `python -m tailoring.apply "<company>" <req_id> --no-prompt --yes` writes a draft to review. Report the folder and the questions in its notes.md. If it says the fit is a skip, ask before adding `--force`. |
| I applied / I heard back | `/radar-applied ...` | `python -m radar.applications add "<company>" <req_id> "<title>"`, or `status "<company>" <req_id> interview`, or `list`. |
| Any replies? | `/radar-mail` | `python -m radar.mail`, then say what moved and what waits for review on the Applied page. |
| Show me different jobs | `/radar-tune <what to change>` | Edit `config.json` or `profile.md` to match, shown as a before and after, applied after they agree. |
| Why am I getting rejected? | | `python -c "from radar import patterns; print(chr(10).join(patterns.summary(patterns.analyse())))"` |
| Open the app | | `python start.py`, then http://localhost:8000 |

## Rules

- Their resume, profile, applications, email and API key never leave the machine, except the calls the radar itself
  makes to Anthropic's API and to employers' career sites. Do not upload or paste them anywhere else.
- Never commit `Resume/`, `profile.md`, `skills_confirmed.md`, `applications.md`, `jobs.jsonl`, `.env`, `digests/`,
  `.cache/` or `notes/`.
- A tailored resume may use only what the base resume and `skills_confirmed.md` already say. Numbers, dates, job
  titles and employers never change. When a posting asks for something they have not shown, ask them; never invent
  it (`docs/RESUME_RULES.md`).
- Be gentle with employer sites: one request at a time with a 1.5 second gap, JSON endpoints only.
- Never submit an application or send an email on their behalf. Drafts are fine.
- Sponsorship information comes from posting wording and public filing data. It is guidance, not legal advice.
