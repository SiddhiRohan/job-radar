# Resume folder map

What was found under `Resume/` on 2026-09-13. The scorer and `apply.py` read this layout through `resumes.py`.
The folder itself is gitignored.

## Bases

| Base | Path | Purpose |
|---|---|---|
| Entry | `Resume/Entry/1 Page/Resume - Siddhi Rohan.docx` (+ `.pdf`) | Entry-level base, framed as about 2 years. One page. Used for New College Grad, junior, I-level, associate, 0 to 2 year roles. |
| Experienced | `Resume/Experienced/V1/DS and DE Resumes/2 Page/Resume - Siddhi Rohan.docx` (+ `.pdf`) | Full base, about 4 years. Two pages. Used for 3+ years, II/mid, senior roles. |

Note: the spec described `Resume/Entry/` and `Resume/Experienced/` directly. The actual layout has one
more level: the experienced variants live under `Resume/Experienced/V1/<role>/<1 Page|2 Page>/`.
The scorer reports variants as `<role>/<one-page|two-page>`; `1 Page` maps to `one-page`, `2 Page` to `two-page`.

## Role subfolders under `Resume/Experienced/V1/`

| Role folder | one-page | two-page | Status |
|---|---|---|---|
| `DS and DE Resumes` | `1 Page/Resume - Siddhi Rohan.docx` (+ pdf) | `2 Page/Resume - Siddhi Rohan.docx` (+ pdf) | Complete. Serves Data Scientist and Data Engineer roles. The two-page file is the experienced base. |
| `AI Engineer` | missing | missing | TODO: empty. `apply.py` will create both variants from the experienced base on first use for an AI or ML Engineer role. |

There is no `ML Engineer` folder. ML Engineer roles use `DS and DE Resumes` until one is created.

## Past tailored versions (`Resume/For <Company>/`)

| File | Guess at purpose |
|---|---|
| `For Amazon/Ring, Blink and Amazon Key Team/Siddhi Rohan - Resume (Data Engineer).docx` (+ pdf) | Data Engineer application to Amazon's Ring/Blink/Key devices org. Different file naming from the bases; headline in the file name. |
| `For Capital One/1 Page/Resume - Siddhi Rohan.docx` (+ pdf) | One-page version for a Capital One application, likely a data role. Capital One does not sponsor, so treat as a formatting reference only. |
| `For Truist/Resume - Siddhi Rohan.docx` | Tailored for a Truist (bank) role. No role subfolder, so the target title is unknown. |
| `For Verizon/Resume - Siddhi Rohan.docx` | Tailored for a Verizon role, target title unknown. |
| `For Verizon/Data Security Engineer/Resume - Siddhi Rohan.docx` | Tailored for a Verizon Data Security Engineer posting. Useful to see how security-adjacent phrasing was handled. |

## Conventions `apply.py` will follow

- New tailored output goes to `Resume/For <Company>/<req_id>_<short-title>/` with `jd.txt`, the resume `.docx`,
  `cover_letter.docx` when required or requested, and `notes.md`.
- Fonts, margins, and section order are read from the base file at build time, not assumed.
