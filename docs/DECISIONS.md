# Decisions made while running unattended

Each entry: what was ambiguous or blocked, what I chose, why. Reverse these if you disagree.

## 2026-09-13, round 2

1. **Resume folder layout differs from the spec.** The spec described `Resume/Experienced/<role>/`, but the
   real layout is `Resume/Experienced/V1/<role>/<1 Page|2 Page>/`. `resumes.py` points at the real paths.
   Variants are reported as `<role>/<one-page|two-page>`; `1 Page` maps to `one-page`.
2. **Years gate uses the regex, not the model.** Per spec the gate is regex-driven ("N+ years ... experience").
   The model also returns `years_required`; when the regex misses (for example "10+ years in software
   engineering" with no word "experience" nearby) the posting is still scored and the model's low score
   handles it. The regex takes the smallest N in the text so a "6 years with BS or 4 with MS" line reads as 4.
3. **Sponsorship sections use the regex tag, not the model's.** The regex result plus the company default is
   auditable in the Skipped section. The model's own read is stored in the verdict for comparison.
4. **Contract detection is narrower than the literal word list.** "contract" alone would flag every
   government-contractor posting (Booz Allen, Leidos mention contracts constantly). Titles match the bare
   words; descriptions need a contract-role phrase (W2, C2C, 1099, contract-to-hire, N-month contract,
   "contract role/position", temporary position).
5. **Rule-decided postings are not sent to the API.** Years-gated, sponsorship "no", and PERM-ad postings get a
   synthetic score of 1 with the reason, so the 120-call cap is spent on postings that can matter.
6. **Empty role subfolder (AI Engineer).** Creating a true one-page variant from a two-page base needs page
   fitting I cannot measure without rendering. I copy the `DS and DE Resumes` variant of the same length and
   rotate the headline, then tailor. The result should be checked visually once.
7. **Approval gate while unattended.** The owner asked to skip the terminal approval this round. `apply.py --yes`
   writes the before/after list into `notes.md` and builds the docx anyway.
8. **Part D tools.** The remove-ai-marks service was not running and neither `exiftool` nor `qpdf` is installed.
   `finalize.py` uses the local fallback: invisible-Unicode strip plus core/app property clearing for .docx.
   No PDFs are produced by this pipeline, so nothing was skipped there. To use the service later, start it and
   set `WATERMARKS_SERVICE_URL` (default `http://127.0.0.1:8765`).
9. **Fabrication guard is word-level.** The first tailoring pass added "scikit-learn", "feature engineering", and
   "anomaly detection", none of which are on the base. I added a guard: bullet rewrites that introduce any 5+ letter
   word absent from the base are reverted into a question; skills not on the base are pruned; the summary gets one
   constrained retry, else the base summary with the headline rotated. The guard cannot catch new phrases built from
   existing words (for example "fraud and abuse detection" from "friendly-fraud" and "detection logic"), so the summary
   still needs a human read. The Adobe run was redone after the guard went in.
10. **Company expansion: web search budget ran out.** The session allows 200 web searches. After the first pass over
    all candidates (one search each) and a second pass over 26 of the misses, the budget was exhausted. The remaining
    57 first-pass misses are recorded in `not_on_workday.json` with `second_search: skipped` and the ATS seen in the
    first search (own site, Greenhouse, Lever, SmartRecruiters, Taleo, Brassring, Oracle, SuccessFactors, Workable).
    Rerun `python ledger.py show` next session to see them; a second search for each is cheap if you want it.
11. **Slug resolution only from URLs actually seen.** Tenant roots return 406 for valid and invalid tenants alike, so
    nothing could be probed. Every slug in `candidates.json` came from a `*.myworkdayjobs.com` URL in a search result.
    Two failures (FactSet on wd1, Expedia on wd5) were retried on a second shard that also appeared in the results.
    Chime's `CSM` site and VMware (absorbed by Broadcom) failed twice and were dropped.
12. **No pushes this round.** The remote stays configured (it is private) but nothing is pushed, per the round-2
   rules.

## 2026-09-14 and 2026-09-15

13. **Do not stack PRs.** PR #11 was based on the folders branch (#10). The owner merged #10 first, then #11 merged into
    the already-merged branch and never reached main; the commit had to be re-opened as #12. From now on every PR
    is based on main; if a change depends on another PR, wait for it to merge.
14. **Prepare is off by default.** Planning every Apply row after the morning run cost about a minute per row for
    something used occasionally. Tailoring is on demand from chat or the Tailor view; `prepare_cap` can be raised
    to turn it back on.
15. **ruff-format versus the 150-line rule.** The formatter expands large literals one item per line, which pushed
    filters.py, expand.py, and skills_extract.py far past 150 lines without adding code. Those literals are wrapped
    in `# fmt: off` / `# fmt: on`. server.py and chat.py are over 150 lines after formatting; splitting them is a
    reasonable follow-up, not urgent.
16. **CI ran plain pytest.** Locally `python -m pytest` adds the working directory to `sys.path`; the runner did
    not, so every test failed to import. `pytest.ini` sets `pythonpath = .`; run tests the same way CI does.
17. **Branch protection.** Unavailable on the free private plan (API 403, rulesets not enforced). The workflow is a
    convention held in CLAUDE.md until the plan changes or the repo goes public.

## 2026-09-17: outreach in Tailor

18. **Reuse the outreach generator.** Call `letters.outreach` unchanged through a background route with
    `profile.md` and visible resume sections. Read editors directly so focused edits are included before blur.
19. **Keep outreach state local to each Tailor render.** Revision guards reject stale responses after opening
    or replanning another state; disabling the button during generation prevents overlapping requests.
20. **Show accessible counts without blocking edits.** Count Unicode code points for the note and
    whitespace-delimited words for the message. Associated live feedback and `aria-invalid` expose the limits;
    deliberate edits remain intact and can be saved even outside those limits.
21. **Save current outreach drafts separately from rebuilding.** Read textarea values at save time so edits
    reach `outreach.md` without another rebuild. Optional outreach preserves existing resume and notes saves.
22. **Keep route tests offline.** Synthetic inputs and mocked generators avoid network calls and optional
    HTTP client dependencies.
23. **Use guarded toast feedback for outreach failures.** Re-enable the button for retry and omit the inline
    outreach error paragraph. An empty `.error` element would make the existing offline timer retry after a
    successful manual recovery, rendering Tailor again and discarding fresh edits. Removing it preserves the
    existing retry machinery and stale-response guard while preventing that interaction.

## 2026-09-17: entry-level sourcing

24. **Titles must name a target role.** The old rule accepted any single word of the search term, so "machine"
    let in Machine Operator and "scientist" let in lab scientists: 541 of 589 kept rows were one-word matches and
    they swamped the 40-row scoring cap. `title_patterns` in config.json now lists the role families. Replayed on
    413 stored postings it keeps 128 and retains 15 of the 18 past Apply verdicts. The three lost are generic
    "Software Engineer" and "Specialist, Engineering" titles; general software engineer was 4 Apply out of 65
    scored, so it stays out unless the title carries entry wording (`entry_title_patterns`).
25. **Entry terms get one page and a 14-day window.** Workday returns "early career", "new college grad", and
    "entry level" by relevance, and those roles stay open for weeks (GM's ML Systems Engineer, Early Career was 8
    days old and never seen with the 1-day window). seen.json prevents repeats. Tier 1 and 2 only; about 280 more
    requests, roughly 8 minutes per run.
26. **Entry-level rows are scored first.** The queue was ordered by search term, so with a backlog the cap was
    spent before entry rows were reached. Order is now entry wording or two years and under, then newest.
27. **include_override never rescues director, VP, manager, principal, or intern titles.** "associate" as an
    override had kept Associate Director and Associate Vice President, and "early career" kept an internship.
28. **Overlapping runs are allowed; duplicates are not.** The owner prefers a second run to proceed rather than be
    refused. `radar/store.py` re-reads the file under a short write lock, appends only keys not on disk, and the
    scorer merges instead of overwriting, so two runs at once store each posting once and lose nothing. On
    2026-09-17 the scheduled run and a UI run both appended the same 176 rows; they were removed (977 to 801,
    backup in .cache/jobs.before-dedupe.jsonl).

## 2026-09-19

29. **Entry-level roles get their own section.** The entry terms added on 2026-09-17 do source junior roles (12 on
    2026-09-18, 8 on 2026-09-19), but the scorer rarely gives them a 4: it marks them down for being a narrow or
    generic fit, which is fair for a senior role and wrong for a new-grad one. With an Apply bar of 4 they all
    landed in the collapsed tail, so the owner saw none of them. `sections()` now returns an `entry` bucket for
    entry-titled postings scoring 3 or better, shown under Apply in the digest and the UI. The Apply bar is
    unchanged; score 2 and below stay in the tail, where the 2027 start dates and hardware roles belong.
30. **The digest selects a day's postings by date, not by the run timestamp.** A second run on the same day writes
    a new `ran_at`, which matched no stored `first_seen`, so digests/2026-09-19.md reported "New postings kept: 0"
    while 49 postings were in fact stored by the 7:30 run. The web UI was always right because it filters by date.
    `prepare.py` had the same comparison.
31. **AGENTS.md is ignored.** A copy of CLAUDE.md keeps reappearing at the repo root, written by something outside
    this project. It was nearly committed once. Ignoring it keeps `git status` readable; delete it freely.

## 2026-09-20: company expansion

32. **Harvest tenants from role searches instead of chasing names.** Six parked names (SAIC, Navy Federal, Liberty
    Mutual, MetLife, Walgreens, Chewy) returned no Workday tenant, but every `site:myworkdayjobs.com` role search
    surfaced real posting URLs for employers not yet covered. Eighteen searches gave 53 tenants; 51 passed the live
    check, 49 were added. Slugs are copied from URLs seen, never guessed. Eli Lilly and Zelis answer 422 on the site
    slug seen and are recorded as failed rather than guessed at. New York Times (a single sub-board with 0 roles) and
    Navient (2 roles) were skipped. The Veralto URL covers only its Esko subsidiary and is named that way.
33. **Sponsorship defaults for the new entries are marked unchecked.** The search budget went to finding tenants, so
    25 large employers are set to sponsors_h1b true with the source "general knowledge, not checked against FY2025
    lists" and sit in tier 2; the other 24 are null in tier 3 (Mondays and Thursdays, one page) and land in Maybe
    rather than Apply. Posting text still overrides either default. NASA JPL is left null on purpose: many of its
    roles carry US-person restrictions. Checking these 49 against an H-1B list is a good next task.
34. **"head" is a seniority exclusion.** The dry run kept "Head, LOB Analytics and Insights" at TD Bank.

35. **The 49 new tenants are now checked against H-1B filings.** Each was looked up on MyVisaJobs, H1BGrader and
    Ellis (DOL LCA data, fiscal year 2025); evidence is in `companies/h1b_check.json` and `expand.py` reads it in
    place of the unchecked list from decision 33. Rule: 10 or more LCAs is true, 1 to 9 or unclear is null, none is
    false. Result: 31 true, 16 null, 2 false. Five guesses were wrong and moved to tier 3 (BD, Cencora, FICO,
    Mimecast, Procter & Gamble); eleven unknowns turned out to be real filers and moved to tier 2, including HHMI
    with 160 LCAs and PRA Group, which files for data engineer and data scientist titles. Hagerty and ProMach show
    no filings and are false. Counts differ between the three sites because they split legal entities differently,
    so the file records the range. NASA JPL files petitions but many of its postings carry US-person wording; the
    posting text handles that.

36. **Capital One is a sponsor, tier 1.** It sat in the no-sponsorship list with the defense contractors because
    many of its postings say "Capital One will not sponsor a new applicant". That sentence is per posting, not
    company policy: it is a top H-1B filer, and the postings without the sentence were read by the scorer as
    sponsoring. The false default tagged those "unlikely", which kept a Senior AI Engineer scoring 4 and two others
    out of Apply. The posting-level check already drops the ones that say no, so the company default is now true.
    Six stored rows were retagged.
37. **A posting that sponsors beats a negative company default.** Capital One showed the general gap: a false
    company default tagged every posting without explicit wording "unlikely", and "unlikely" was treated as a no.
    Now "unlikely" skips only when the scorer did not read the posting as sponsoring, and a model read of "yes"
    is enough for Apply under an unknown or negative default. A posting that says no still loses under any
    default. Replayed on stored data nothing else was buried; only the four defense contractors carry "unlikely"
    rows and the scorer agrees with all of them. The Today view also lists the Skipped rows, collapsed, so a
    wrong skip can be seen rather than silently lost.

## 2026-09-24: README

38. **README screenshots use demo data.** The real Today view carries notes about the owner's own projects and the
    Applied view shows where he applied. Git keeps images forever, including if the repo goes public, so the
    screenshots come from a throwaway copy of the app: the same public postings, neutral fit notes, and four
    made-up applications. Captions say so. The banner was generated with Higgsfield (GPT Image 2.5) and saved as a
    17 KB WebP.

## 2026-09-25: statuses from email

39. **IMAP with an app password, not the Gmail API.** A personal Google Cloud app in testing mode loses its sign-in
    every seven days, which would break the unattended 7:30 run weekly. An app password does not expire, is revoked
    in one place, and IMAP is in the standard library. The folder is opened read-only and bodies are fetched with
    `BODY.PEEK`, so nothing in the mailbox changes.
40. **Automatic only with a requisition id.** The owner's rule: a status changes on its own only when an email contains
    the id of exactly one application and its wording is clear. Everything else that looks like hiring mail goes to
    review. Automatic changes only move forward (applied, screen, interview, rejected, offer), because a delayed
    confirmation must not undo an interview; a person settling a review item can move a status any way.
41. **Rejection wording is checked first.** Rejections usually also say "thank you for applying", and phone screens
    mention interviews, so the rules run rejected, offer, screen, interview, applied.
42. **The first real mail run was wrong, and the rules were recalibrated on it.** It moved 14 statuses; 8 were false
    interviews, because confirmation emails say things like "you will be contacted if you're selected for an
    interview" and the rule matched the bare word. All 14 were undone from a backup taken just before the run. Against
    the 179 hiring emails from that run, read once into a temporary file and deleted after: interview and screen now
    need invitation wording, phrases after "if", "may", "might" or "should" are ignored, curly apostrophes read as
    straight, and two missed rejection wordings were added. Result on the same emails: 6 rejections applied
    automatically, 14 rejections without an id to review, no false interviews. Plain confirmations no longer go to
    review, a deliberate change from the owner's first rule: they cannot move a status and filled the list with 35
    items. Paraphrases of the misread boilerplate are now regression tests.
43. **The second rule set missed rejections, and one old-rule run slipped through.** The owner found one application at
    interview again. Reading both of its emails: a confirmation ("contact you to arrange an interview if the role is
    a good match") and a rejection ("have decided not to move forward for the ... role"). Two causes. The
    running server still held the first rules in memory after the fix merged, and a Check mail pressed before the
    restart used them; the restart then cut that run off before it saved its record. And the second rules read the
    rejection as a confirmation, because "decided not to" was not covered. The first calibration only compared the
    old rules with the new ones, so a wording both missed went unnoticed. A fresh scan of every hiring email for
    rejection-style words found four more: "won't be able to move forward", "aren't moving forward", "does not align
    ... with", "pursuing other applicants". All are covered now; every one of the 28 rejections the rules find was
    checked by its triggering phrase, and the only rejection-style words left unmatched are conditional ("if you are
    not selected", "if the position is filled"). Review guesses now come from the sender and subject before the body,
    because every Workday email names Workday in its footer. Lesson: restart the server as part of merging a rule
    change, and calibrate against the emails themselves, not against the previous rules.

## 2026-09-25: public for an afternoon, then brand

44. **Personal details never in tracked files.** The owner made the repo public for a few hours. Old commits carry
    `jobs.jsonl`, `skills_confirmed.md` and early run data; the docs named the owner, their visa status and specific
    applications. The repo is private again. Per the owner's wish the history is untouched, and the current tree is
    scrubbed: name, resume file name, personal stopwords and overlap notes live in `.env` and the ignored `Resume/`
    folder (`radar/owner.py`). If the repo ever goes public again, it should be a fresh repo with no history.
45. **Brand.** Three logo concepts were generated with Higgsfield; the frosted teal disc (concept A) was chosen
    because it reads at 16 pixels and matches the existing mark. The ident video is a 6 s Seedance render from the
    logo; the README shows it as an 800 px animated WebP because GitHub does not play repo-hosted mp4 files.
    `docs/img/social-preview.png` is for the repository's social preview setting, which only the web UI can set.

## 2026-09-25: the postings behind applications

46. **A taken-down Workday posting answers 403, not 404.** Checked against a posting the owner was rejected from: the
    detail endpoint returns `403 {"errorCode":"S22","message":"permission denied"}`, while a path that never existed
    returns 404 `S21`. The watcher treats 403 as closed only when Workday's JSON error body is present, so a
    firewall block or an outage (usually HTML) stays "unknown" and never reads as a closure. Closures and changes
    keep the date first seen; a posting that comes back drops its closure. Applications already rejected or at
    offer are not checked, which keeps the daily run to one request per open application.
