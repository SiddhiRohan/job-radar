# Resume tailoring rules

Read by `apply.py` on every run. These are the rules Rohan set; do not relax them.

## Where to start
- Start from the base the scorer recommended (`entry` or `experienced`), and from the matching role and
  length variant under `Resume/Experienced/V1/<role>/<1 Page|2 Page>/` if it exists.
- If the role subfolder is empty, first create that role's one-page and two-page resumes from the base
  (copy the `DS and DE Resumes` variant of the same length and rotate the headline), save them in the
  subfolder, then tailor from there.

## Assess fit before touching anything
- Check sponsorship exclusions, PERM-ad patterns, the years gate (6+ years required means skip), and
  platform tools Rohan lacks (Databricks, Snowflake, Azure, GCP, Power BI, SAS).
- If the assessment says skip, say so plainly and stop unless `--force` is passed.

## What may change and what may not
- LOCKED: header, employer names, titles, dates, GPA, and every number.
- Tailor by mirroring the JD's phrasing in the summary, reordering bullets by relevance, adjusting the
  Skills line, and picking coursework.
- Headline rotates between Data Engineer, Data Scientist, ML Engineer, AI Engineer by role.
- Inline bold on methods, domain terms, and headline metrics.
- Never fabricate. Only tools and experience already on the base resume. If a bullet needs something
  new, write it in `notes.md` as a question for Rohan; do not put it in the resume.

## Review gate
- Print every changed bullet as before/after in the terminal for approval BEFORE building the docx.
  No approval, no build. (`--yes` skips the prompt; the before/after list still goes into `notes.md`.)
- Flag any bullet that would be hard to defend in an interview.
- Note the one-line explanations for date overlaps: Kridha concurrent with StackNexus, two concurrent
  AREC roles, two concurrent Adventaus roles.

## Length and style
- The experienced base stays two pages, the entry base stays one. Cover letters are one page.
- No em dashes anywhere.
- Match the base resume's fonts, margins, and section order exactly; read them from the base file.

## Cover letter
- Role and company specific. Adds to the resume rather than repeating it. Plain human voice, no
  buzzwords, no visa mention.

## Outreach (`--outreach`)
- LinkedIn connection note under 300 characters (aim 250 to 270).
- DM or application message 100 to 120 words.
- No name sign-off on LinkedIn messages. No visa mention in cold outreach.
