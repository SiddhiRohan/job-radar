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
