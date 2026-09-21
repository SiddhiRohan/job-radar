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
7. **Approval gate while unattended.** Rohan asked to skip the terminal approval this round. `apply.py --yes`
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

13. **Do not stack PRs.** PR #11 was based on the folders branch (#10). Rohan merged #10 first, then #11 merged into
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
28. **Overlapping runs are allowed; duplicates are not.** Rohan prefers a second run to proceed rather than be
    refused. `radar/store.py` re-reads the file under a short write lock, appends only keys not on disk, and the
    scorer merges instead of overwriting, so two runs at once store each posting once and lose nothing. On
    2026-09-17 the scheduled run and a UI run both appended the same 176 rows; they were removed (977 to 801,
    backup in .cache/jobs.before-dedupe.jsonl).

## 2026-09-19

29. **Entry-level roles get their own section.** The entry terms added on 2026-09-17 do source junior roles (12 on
    2026-09-18, 8 on 2026-09-19), but the scorer rarely gives them a 4: it marks them down for being a narrow or
    generic fit, which is fair for a senior role and wrong for a new-grad one. With an Apply bar of 4 they all
    landed in the collapsed tail, so Rohan saw none of them. `sections()` now returns an `entry` bucket for
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
