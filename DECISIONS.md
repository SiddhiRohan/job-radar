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
9. **No pushes this round.** The remote stays configured (it is private) but nothing is pushed, per the round-2
   rules.
