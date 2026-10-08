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
    every hiring email from that run, read once into a temporary file and deleted after: interview and screen now
    need invitation wording, phrases after "if", "may", "might" or "should" are ignored, curly apostrophes read as
    straight, and two missed rejection wordings were added. Result on the same emails: rejections carrying an id
    applied automatically, the rest went to review, and no false interviews. Plain confirmations no longer go to
    review, a deliberate change from the owner's first rule: they cannot move a status and filled the list with
    noise. Paraphrases of the misread boilerplate are now regression tests.
43. **The second rule set missed rejections, and one old-rule run slipped through.** The owner found one application at
    interview again. Reading both of its emails: a confirmation ("contact you to arrange an interview if the role is
    a good match") and a rejection ("have decided not to move forward for the ... role"). Two causes. The
    running server still held the first rules in memory after the fix merged, and a Check mail pressed before the
    restart used them; the restart then cut that run off before it saved its record. And the second rules read the
    rejection as a confirmation, because "decided not to" was not covered. The first calibration only compared the
    old rules with the new ones, so a wording both missed went unnoticed. A fresh scan of every hiring email for
    rejection-style words found four more: "won't be able to move forward", "aren't moving forward", "does not align
    ... with", "pursuing other applicants". All are covered now; every rejection the rules find was
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

46. **A taken-down Workday posting answers 403, not 404.** Checked against a posting known to be taken down: the
    detail endpoint returns `403 {"errorCode":"S22","message":"permission denied"}`, while a path that never existed
    returns 404 `S21`. The watcher treats 403 as closed only when Workday's JSON error body is present, so a
    firewall block or an outage (usually HTML) stays "unknown" and never reads as a closure. Closures and changes
    keep the date first seen; a posting that comes back drops its closure. Applications already rejected or at
    offer are not checked, which keeps the daily run to one request per open application.

## 2026-09-26: thirty score-4 postings a day

47. **Volume comes from the search, not the scorer.** The owner wants at least 30 score-4 postings a day; recent
    days gave 6 to 14 from 35 to 101 kept. The score cap was not the limit (no posting went unscored), so the
    levers are upstream: every tier daily, three pages for tier 2 and two for tier 3, "analytics" as a fifth term,
    and the cap raised to 120 so it stays out of the way. "Sr" and "Sr." leave `exclude_seniority`: "Senior" was
    never excluded, and across 927 scored postings Senior titles scored 4 at the same 10 percent rate as the
    rest, so the abbreviation was removing matches for no reason. Estimated run time goes from about 32 to about
    an hour. Google is not on Workday (own careers site), so it cannot appear until a non-Workday adapter exists
    (issue #1); the same holds for every name in `companies/not_on_workday.json`.

## 2026-09-27: rejections by the role they name

48. **A rejection names its role, so the role is enough.** Every email waiting in Needs review at the time was a
    rejection without a requisition id the rule could match, and every one named the role. The owner asked for "not moving
    forward" and similar to go straight to rejected. Rejections only: an offer or an interview invitation without an
    id still waits for a person, since a wrong one of those costs more. The match is the employer (sender address,
    then sender and subject) plus the application's whole title as words in the subject or the first 1,500
    characters, so footers listing other openings never match; a title directly after "Senior", "Associate" and the
    like, or before a level such as "II", belongs to a longer title and does not count. Two applications with the
    same title still go to review. A rejection for a role not on the list, or from an employer with nothing open,
    is filed under "Rejections for roles not on your list" rather than added as an application: the radar records
    what the owner applied to through it, and guessing a company and title from free text would put wrong rows in
    the table. In a dry run every moved application was checked by title against its requisition; one email needed its full
    body, not the stored snippet, to name its role.

## 2026-09-27: the fit, factor by factor

49. **The fit is shown factor by factor, with evidence; sponsorship, location and pay by rule.** A score and a
    two-sentence why said how good a fit was but not on what evidence, and the owner wants postings judged on
    experience, not on shared keywords. The verdict now lists four factors (experience, level, skills, domain),
    each with a verdict word and a short quote or paraphrase from the posting and from the resume, so a score can be
    checked against the text instead of taken on trust, and a wrong one shows where it went wrong. Experience means
    the same kind of work at the depth asked, judged against the better-fitting base. Sponsorship, location and pay
    are facts the pipeline already reads: the tag and phrase from `sponsor.py` with the company default (plus
    Claude's stored read, which the digest already uses), the Workday location fields, and the `salary.py` range.
    Computing them costs no tokens and cannot contradict the section a posting sits in, because the sponsorship
    badge calls the digest's own `says_no` and `sponsors`. No location or pay preference is configured, so any US
    location meets, with remote or hybrid named only from the location strings or clear wording ("fully remote",
    "hybrid work schedule"; never "remote sensing", "hybrid cloud" or a negated phrase), and pay meets when a range
    is stated, is partial when it is not, and is never a gap.
50. **Factors come before the scores; older verdicts stay as they are.** "factors" is the first property of the
    schema and the prompt says to fill it first, so the evidence is written before the scores, which must agree with
    it. The existing fields and their meaning are unchanged, but what the scores are conditioned on is not: compare
    the first runs' score-4 counts with the recent 6 to 14 a day. Moving "factors" to the end of `PROPERTIES` in
    `radar/fit.py` restores the old order. The schema cannot require exactly four factors (array and string length
    keywords are not supported, like minimum and maximum), so the prompt asks for four in order and
    `model_factors()` keeps the first entry for each known name and drops anything else. The added output is about
    200 to 400 tokens per scored posting, 0.3 to 0.6 cents at Sonnet 4.6 output prices and under a dollar a day at
    the 120 cap; `max_tokens` rises from 1024 to 1536 so a longer verdict is never cut off mid-JSON. Verdicts stored
    before this have no "factors" key and get no table and no gaps line, rather than three rule rows that would look
    broken; rescoring them would cost a call each. Rule verdicts (years gate, sponsorship no, PERM ad) store an empty
    list because no model read the posting; the drawer shows their three rule rows, and the why line names the rule.

## 2026-09-27: ready for other people

51. **Public from a fresh repository, not this one.** An audit before going public found the author's resume, a
    skills file, scored postings and a first digest in commits from 13 September, two personal email addresses in
    commit metadata, and five pull request descriptions naming real applications. Rewriting history would not clean
    it: GitHub keeps every pull request's commits reachable, and only GitHub Support can purge them, and the owner
    does not want history rewritten. So this repository stays private as the full record, and the public one starts
    from a clean snapshot. The current tree is scrubbed (tests use fictional employers such as Contoso), and a
    pre-commit privacy guard blocks any commit containing a term from `.privacy-terms`, the owner settings in `.env`,
    or a requisition id in `applications.md`. It reports matches by position, never the term, so its output is safe
    anywhere.
52. **Setup is a script, not an installer.** The owner ruled out a desktop app. `start.py` uses only the standard
    library so it runs before anything is installed; it makes `.venv`, installs again only when `requirements.txt`
    changes (a hash stamp), copies `.env.example`, runs the doctor and opens the app. Thin wrappers make it a
    double-click on Windows and macOS. Development tools moved to `requirements-dev.txt` so a first start installs
    less.
53. **The app schedules the run, and a lock keeps runs single.** A laptop asleep at 7:30 missed the day, and the app
    could not see a run the operating system started. While open, the app now runs at `run_time` and catches up when
    it opens; `run.py` takes `.cache/run.lock` for its whole life, so the app, the system scheduler and a terminal
    never overlap. Nothing runs until the doctor finds nothing to fix, because a first start with no resume polled
    for an hour against nothing. A failed start waits two hours. A lock older than four hours is treated as left by a
    machine that shut down mid-run.
54. **Only the app's own page may write.** The setup page accepts a resume and an API key, and any website open in
    another tab can send requests to localhost. Writes now need no origin (a terminal) or a local one. The key is
    checked with a token count, which is free, stored only in `.env`, and never sent back to the browser.
55. **Two ways in, one set of files.** People who use a coding assistant get `CLAUDE.md` as an operating guide, with
    short slash commands that call the same Python commands the app uses; `AGENTS.md` points other assistants to it.
    The rules for changing the code moved to `CONTRIBUTING.md`. Public docs use this project's own vocabulary and
    name no other product.
56. **The morning brief needs no model.** Its value is judgment, and the judgment is already on disk: fit scores and
    factor gaps, sponsorship, pay, mail events, watcher closures, rejection patterns. Picks rank by best fit, then a
    posting that can sponsor, then stated pay, then newest; the reason is the first factor gap, else the start of the
    why. Changes count since the previous brief, not since midnight, so a second run on one day repeats nothing.
57. **The system schedule is the person's switch.** Changing a computer's scheduler is theirs to decide, so it is a
    button on the Setup page and a command, never done by a run. The doctor reports which way the radar runs.

## 2026-09-27: job boards beyond Workday

58. **A job board is read whole, once per run.** Greenhouse, Lever and Ashby publish every open posting of an
    employer, with its full description, in one public JSON response, and none has a search that behaves like
    Workday's. So the radar fetches the board once, through `wd.request_json` (the same 1.5 s gap, retries and
    6-hour cache), and gives each posting the Workday path's rules: the title must pass `title_matches_term` for a
    search or entry term whose date window the posting is in, then the seniority, domain and US rules, with keys
    `company|id` as before. Entry terms stand in for Workday's relevance search, which a board lacks, so they count
    only for titles with entry wording (the same `is_entry_title` that widens the title patterns); otherwise every
    matching title up to 14 days old would pass as an entry find. The description that came with the listing is the
    detail record, so years, sponsorship and contract flags are read from it without a second request. Board
    postings have no Workday detail path, so the posting watcher and a pasted URL in Tailor still cover Workday only.
59. **Dates.** Greenhouse's `first_published` is the posting date. `updated_at` moves whenever the employer edits the
    board (on the Databricks board hundreds of postings shared one timestamp), so it is used only when
    `first_published` is missing. Lever gives `createdAt` in epoch milliseconds, Ashby `publishedAt`. Age is counted
    in UTC calendar days and written in Workday's words ("Posted Today", "Posted 3 Days Ago", "Posted 30+ Days
    Ago"), so pages and digests read alike. A posting without a date counts as 999 days old, outside every window.
60. **Places and the US rule.** One US place keeps a posting, as Workday's additional locations do. Lever gives the
    first place's ISO country and Ashby a country for every place; where a country is given, it decides. Greenhouse
    gives only free text, sometimes several places joined by ";" (split apart) or by commas (left alone, since "San
    Francisco, California" is one place), so its places are judged by the words in `filters.NON_US`. Against 745
    distinct Greenhouse places on 15 live boards the words missed Serbia, Ukraine, Estonia, Cyprus, Slovenia,
    Lithuania, Canadian provinces, EMEA and "São Paulo" with its accent; those were added, none of them a US place
    name. Still wrong and not new: "Vancouver, WA", "Dublin, CA" and lists such as "SF, NYC, Toronto" read as non-US,
    because a non-US city name wins unless "US" or "United States" is in the text. Workday's listing check has the
    same gap; its detail record's country code covers it there.
61. **Pay and ids.** Ashby keeps pay out of the description, in `compensation`. When the description has no range,
    its salary summary goes in front as "Pay range: ..." so `salary.py` reads it (223 of 349 Snowflake postings gain
    a range). Lever's `salaryRange` is used the same way, but neither live Lever board carried one, so that branch
    follows Lever's documented shape only. The requisition id is the board's posting id; Greenhouse's own
    `requisition_id`, the one an employer's emails quote, is not stored, so their emails match by role name.
62. **Seeding: 18 employers, one request each.** Every token was confirmed by one request to the board the poll
    reads, 21 requests in all (the cap was 60): the seven employers `not_on_workday.json` notes as Greenhouse or
    Lever, and eleven whose own careers site fronts a board. Greenhouse's `company_name` matched the employer every
    time. DoorDash's board is `doordashusa`; HubSpot's `hubspot` board exists but is empty and `hubspotjobs` is the
    live one. Wayfair and Rivian answered 404 on Greenhouse and stay in `recheck_later.json` with what was tried;
    the employers now polled leave that file. Sponsorship comes from `expand.py`'s lists: 12 are on the H-1B list,
    and Dropbox, Chime, Robinhood, Okta, HubSpot and Spotify are on none, so null. All 18 are tier 2, the six
    unknowns included, because that was the default asked for; `python -m companies.expand` recomputes tier from
    sponsorship and would move those six to tier 3, so recording their filings in `companies/h1b_check.json` is the
    durable fix and a good next task. Screened offline with the current config, the saved responses give 2 postings
    in a 3-day window (a weekend) and 27 over 14 days across 11 of the 18 employers.

63. **Batch scoring is a setting, off by default.** Batches cost half as much but answer in minutes to an hour, and
    the digest, brief and email all wait on scoring, so turning it on is the person's call, not a default. One
    batch per run, each request named by its position (`p0`, `p1`, ...) because custom ids allow only letters,
    digits, `_` and `-`, which company names do not keep to. The run waits up to 60 minutes, polling every 30
    seconds; a batch still running then is cancelled and whatever finished is read before the rest is asked
    directly, so nothing is paid for twice. A request that errored, expired or came back cut off is asked directly
    too, which also covers a model the key cannot use. Pasted links stay direct: someone is waiting on the answer.
    If the machine sleeps mid-wait, the batch still finishes and is billed, but its answers are not collected and
    the next run scores those postings again; keeping the batch id to collect them later is left for when it
    happens in practice. In a live check, a one-posting batch with the structured-output schema answered in 94
    seconds with all four factors.

64. **One task name, checked by folder.** Windows Task Scheduler and launchd hold one daily entry named JobRadar
    and `com.jobradar.daily`. A name per folder would let two copies each keep a schedule, but it would stop
    recognizing a JobRadar task made by hand before the setup page existed, and the author's machine has exactly
    that. So the name stays, and status, install and remove look at the folder the entry starts in: a copy
    whose folder is not in the entry reports no schedule, removes nothing, and refuses to install over it with a
    message saying another copy holds the task. The folder must end where an entry the radar writes has it end
    (before `\.cache\run-daily.cmd`, a closing quote, or `&&` in a task made by hand), so "job-radar - Copy",
    "job-radar (1)" and a copy nested inside another are all other copies. A task whose folder no longer exists
    can only fail, so any copy may replace or remove it. Cron keeps a line per copy, told apart the same way.
    Found by starting a fresh clone next to the author's install: its setup page said it ran every morning and
    offered to stop a task that belonged to the other folder; a review then found the lookalike and moved-folder
    cases.

65. **A coding assistant can score instead of an API key.** Someone using the radar through Claude Code already pays
    for a model, so asking them for a second, metered key is a reason to leave. `radar.handscore` hands the
    assistant exactly what the scorer sends the API (the rules and schema from `radar/fit.py`, the profile and both
    bases) and takes back verdicts only after checking them against the same schema, plus the factor order the
    schema cannot state, so a verdict from either path reads the same in the digest, the drawer and the brief. The
    check is a small reader for the part of JSON Schema that `fit.py` uses rather than a new dependency. Postings a
    rule settles are left to the run, which settles them without a model. Verdicts are marked `scored_with:
    "assistant"`, so their share can be compared with the API's later. The app's own morning run still waits for a
    key; `python run.py` without one finds and filters, and the assistant scores when asked.

66. **The intro video.** About 47 seconds, cut like a TV spot at the owner's request: four students in a sunny
    apartment kitchen react as the radar's morning brief spreads between them, with hard cuts on the beat,
    full-screen close-ups of the real app on demo data with fictional employers, questions typed the way the in-app
    chat takes them, and a white end card with the line "Apply where you're wanted." Every shot carries a short
    caption saying what is happening, so the story reads with the sound off, as most people first watch. Every claim
    in it can be checked against the code. The live-action shots were generated with Seedance 2.5, 4 seconds each at
    48 credits: one shot of the four friends came first and every later shot used it as a reference, so the same
    people appear throughout, and the lead is the student from the earlier morning shot. The music is “Feel Alive”
    by Michael Ramir C., from Mixkit, under its free stock music license: use in videos on any web platform, no
    attribution required, no redistribution on its own, so only the finished video is in the repo, and the README
    credits it anyway. A first cut with music synthesized in code sounded wrong to the owner and was dropped. GitHub
    does not play video files from a repository inline, so the README plays the whole video as a silent animated WebP
    (10 frames a second, under 5 MB) linked to the MP4 with sound. At the owner's request it carries no "watch with
    sound" badge or link text.

67. **Four agents, chosen for what only this radar can see.** Interview prep, follow-up drafts, skill gaps and the
    sponsor map each read records a general assistant does not have: the posting as it was on the day it was found,
    its fit factor by factor, the email that moved the application, the watcher's word that the posting is still up,
    and a month of verdicts. Two need judgment over free text and use the model; two are counts and use none, so
    they cost nothing and cannot invent anything. None of them sends, submits or applies: drafts are copied and sent
    by the person, and a prep is something to read. They live in `radar/` like the watcher and the rejection
    patterns, one module each, with `radar/agents.py` running the two that write.

68. **When each agent runs.** A prep is written when an application reaches a screen or an interview, once per
    stage, because a prep for every application would spend money on the many that never get a reply; any
    application can still have one by name. A follow-up waits ten days, the brief's own quiet threshold, skips a
    posting the watcher found closed, since a note about a filled role is wasted, and is written once per
    application. Each run writes at most five of each (`per_run`), the oldest quiet applications first, so a first
    run on a long list does not surprise anyone with a bill. A draft leaves the list when it is marked sent or
    dismissed, when its application moves on, or when its posting closes. Skill gaps read thirty days of verdicts
    and the sponsor map sixty days of postings: the skills asked for change with the market, sponsorship wording
    less often.

69. **Numbers in a prep or a draft come only from the posting and the resume.** Tailoring already locks numbers
    (`docs/RESUME_RULES.md`). A prep is read aloud in an interview and a draft goes out under the person's name, so
    an invented "cut latency by 40%" does more harm there. `radar/facts.py` replaces any figure not found in what
    the agent was given with [?] and names it in the notes, whatever its units: 40%, 800ms, $2B, a 12-person team
    and 2019-2021 are all checked, and 1,200 and 1200 count as the same number. Digits that belong to a name or a
    ratio (H-1B, S3, GPT-4, Neo4j, 1:1, 24/7) are not figures; a first version checked them too and could turn a
    sponsorship answer into "H-[?]B". Any number in a source counts, inside a date or a name too, and the sources
    include the employer's name (3M) and the application date: the first live run took the 14 out of "applied
    September 14". A LinkedIn note over 300 characters goes back to the model once with the problem named, then is
    kept with a note, since a long draft is still worth trimming by hand.

70. **No API key: the coding assistant writes; one application at a time by name.** As with hand scoring,
    `python -m radar.agents next` puts every due task, with each agent's rules and schema once, in
    `.cache/agent_tasks.json` (`radar/agenttasks.py`), and `save` stores an answer only after the same schema check
    the API path gets, plus the agent's own length and count checks. The schema reader is the one in
    `radar/handscore.py`; its message for an unknown field now says "not in the schema". Asked for one employer, in
    the chat or with `--for`, an agent writes for one application only: for a prep the newest at a screen or
    interview, else the newest; for a follow-up the quietest still waiting for a reply, and none when every
    application there has had one. A name matches exactly, in any case, or by a prefix only one employer has, so
    "GE" never reaches Target or Geico. In the chat an existing prep or draft is returned rather than rewritten,
    even once a draft is marked sent. One writing run happens at a time in the app, none while the morning run is
    going, and the state files are written whole under the jobs lock, so a click and the morning run never lose each
    other's work; an unreadable state file reads as empty instead of stopping the brief.

71. **Skill names from free text; sponsorship from wording first.** The skills factor's "Missing: ..." note, the
    hard requirements and the not-have tools are free text. `radar/gaps.py` keeps the first clause, drops
    parentheses, years and anything over three words, splits on and, or, slashes and commas, folds a few aliases
    (Google Cloud is GCP), and drops words too broad to act on (AI, ML, API). A skill must be missing from two
    postings to be listed. The sponsor map reads a posting as no when its wording rules sponsorship out, it reads as
    a PERM ad, or the model read a no, the same order the digest uses, and as yes when either says so. It flags a
    default only when its own postings clearly disagree: a sponsor whose three or more postings, three in four of
    them at least, rule it out while none says yes, or a no or missing default with a posting that says yes. It
    never edits `companies.json`; the person decides.

72. **One follow-up per employer at a time, from the first real runs.** The first two morning runs drafted three
    follow-ups to one employer, one per role, and the next run would have added two for another. A recruiter who
    gets three notes in a week stops reading them, so `radar/followup.py` holds an employer back while a draft for
    it is waiting or one was written in the last 14 days, and drafts for its oldest quiet role first. Asked for
    notes under 300 characters, the model wrote 291 to 319, so one in ten went back for a rewrite and one stayed too
    long; it is now asked for 280, and the check still holds LinkedIn's limit of 300. The same runs showed the brief
    announcing four of the previous day's drafts again: they were written in the same minute as that day's brief,
    and the brief counted from that minute rather than after it.

73. **The debrief works from the person's own account, and every round feeds the next.** Only the person knows what
    was asked and how it went, so the debrief is written on demand from their account rather than on a schedule: the
    chat, the Agents view, `/radar-debrief` or `python -m radar.agents debrief` keep the account first
    (`radar/debrief.py`), then the usual runner writes it with the API, or a coding assistant does through `next`
    and `save`, so an account given without a key is never lost. A second account before the debrief is written adds
    to the first; one given after starts the next round. Each round's weak answers, concerns and next steps go into
    that round's successor and into the next prep for the role, under their own heading. Numbers may come from the
    account as well as the posting and resume, since the person said them. The thank-you note is a draft they send,
    never sent. The command line moved to `radar/agentcli.py` so `radar/agents.py` stays the runner.

74. **The filter auditor checks the rules against what they threw away.** Most postings never reach scoring: a title
    naming no target role, a seniority or domain word, or a place outside the US drops them, and until now nothing
    kept them, so a rule that was too tight could not be seen. The poll now logs each drop (`radar/dropped.py`), two
    weeks of them and one row per posting and rule. Once a week, when at least 20 were logged, `radar/audit.py`
    sends the model the titles each rule dropped most often, one example and a count per title (25 off-target, 15
    seniority, 10 domain, 5 location), so a few dozen lines stand for hundreds of drops; postings the fixed rules
    skipped for sponsorship or years go too, with the words that decided it, so a misread can be caught even though
    those rules are not settings. The model names the items worth seeing by id, and suggests at most four changes; a
    change that cannot be made as written (removing an entry that is not there, a pattern that does not compile) is
    left out and noted. Nothing touches `config.json` until the person applies a change, which `radar/configedit.py`
    makes one entry at a time, keeping the file's layout. One audit a week costs a few cents.

75. **Co-authored commits are back.** The owner earned GitHub's Pair Extraordinaire badge for a co-authored PR and
    asked for more like it, so commits and squash merges carry Claude as co-author again; PR descriptions still
    carry no tool name. CONTRIBUTING.md now says a co-author trailer is fine and other attribution is not.
