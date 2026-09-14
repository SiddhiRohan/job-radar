"""Parse a base resume .docx into blocks, get a tailoring plan from Claude, apply it without touching formatting."""

import copy
import re

HEADINGS = ("PROFESSIONAL SUMMARY", "WORK EXPERIENCE", "RESEARCH PUBLICATIONS", "SKILLS", "EDUCATION", "PROJECTS")
DATE = re.compile(r"(19|20)\d\d\s*$|Present\s*$")


def marked_text(p):
    """Paragraph text with **...** around bold runs, so inline bold survives a rewrite."""
    out, bold = "", False
    for r in p.runs:
        if bool(r.bold) != bold:
            out, bold = out + "**", not bold
        out += r.text
    return (out + ("**" if bold else "")).replace("****", "")


def parse(doc):
    """Locate summary, job blocks (header + bullets), skills line, coursework line by paragraph index."""
    ps, section, info = doc.paragraphs, None, {"summary": None, "jobs": [], "skills": None, "coursework": None}
    for i, p in enumerate(ps):
        t = p.text.strip()
        if not t:
            continue
        if t.rstrip("\t").upper() in HEADINGS:
            section = t.rstrip("\t").upper()
            continue
        if section == "PROFESSIONAL SUMMARY" and info["summary"] is None:
            info["summary"] = i
        elif section == "WORK EXPERIENCE":
            if "|" in t and DATE.search(t) and any(r.bold for r in p.runs):
                info["jobs"].append({"header": i, "bullets": []})
            elif info["jobs"]:
                info["jobs"][-1]["bullets"].append(i)
        elif section == "SKILLS" and info["skills"] is None:
            info["skills"] = i
        elif section == "EDUCATION" and t.lower().startswith("coursework"):
            info["coursework"] = i
    return info


def set_text(p, marked):
    """Replace a paragraph's text, keeping its style and the first run's font; **segments** become bold."""
    # copy formatting from the dominant run (most text), not the first: headers often start with a tiny spacer run
    template = copy.deepcopy(max(p.runs, key=lambda r: len(r.text.strip()))._r) if p.runs else None
    for r in list(p.runs):
        r._r.getparent().remove(r._r)
    for k, seg in enumerate(re.split(r"\*\*", marked)):
        if not seg:
            continue
        run = p.add_run(seg)
        if template is not None:
            rpr = template.find("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}rPr")
            if rpr is not None:
                run._r.insert(0, copy.deepcopy(rpr))
        run.bold = bool(k % 2)


def reorder(doc, job, order):
    """Move bullet paragraphs so they follow the header in `order` (indices into job['bullets'])."""
    ps = doc.paragraphs
    anchor = ps[job["header"]]._p
    for idx in order:
        el = ps[job["bullets"][idx]]._p
        anchor.addnext(el)
        anchor = el


def new_terms(text, base_lower):
    """Words of 5+ letters in `text` that appear nowhere on the base resume: a fabrication signal."""
    words = set(re.findall(r"[A-Za-z][A-Za-z\-]{4,}", re.sub(r"\*\*", "", text)))
    return sorted(w for w in words if w.lower() not in base_lower)


def apply_plan(doc, info, plan, extra_allowed=""):
    """Apply the plan; return [(where, before, after)] for the terminal diff and notes.md.
    Guards: bullet rewrites that add terms absent from the base are reverted and turned into questions;
    skills not on the base are pruned; the coursework label and leading tabs are preserved."""
    ps, changes = doc.paragraphs, []
    base_lower = "\n".join(p.text for p in ps).lower() + "\n" + extra_allowed.lower()  # base + skills_confirmed.md

    def change(where, idx, new):
        old = marked_text(ps[idx])
        lead = re.match(r"\s*", old.replace("**", "")).group(0)
        new = lead + new.lstrip() if lead and not new.startswith(lead) else new
        if new and new.strip() != old.strip():
            set_text(ps[idx], new)
            changes.append((where, old, new))

    unsupported = new_terms(plan["summary"], base_lower)
    if unsupported:
        plan["questions_for_rohan"].append(
            "Summary uses terms outside the base resume and skills_confirmed.md: " + ", ".join(unsupported)
        )
    change("summary", info["summary"], plan["summary"])
    for pj in plan["jobs"]:
        job = info["jobs"][pj["job"]]
        for rw in pj["rewrites"]:
            if not 0 <= rw["bullet"] < len(job["bullets"]):
                continue
            added = new_terms(rw["text"], base_lower)
            if added:
                plan["questions_for_rohan"].append(
                    f"Reverted job {pj['job']} bullet {rw['bullet']} rewrite: it added "
                    f"{', '.join(added)}. Is that accurate? Proposed: {rw['text']}"
                )
                continue
            change(f"job {pj['job']} bullet {rw['bullet']}", job["bullets"][rw["bullet"]], rw["text"])
        order = [i for i in pj["order"] if 0 <= i < len(job["bullets"])]
        if order and order != sorted(order) and len(set(order)) == len(job["bullets"]):
            changes.append((f"job {pj['job']} order", " ".join(map(str, range(len(order)))), " ".join(map(str, order))))
            reorder(doc, job, order)
    skills = [s.strip() for s in plan["skills"].split(",")]
    pruned = [s for s in skills if s and s.lower() not in base_lower]
    if pruned:
        plan["questions_for_rohan"].append(
            "Dropped skills not on the base resume or in skills_confirmed.md: " + ", ".join(pruned)
        )
    change("skills", info["skills"], ", ".join(s for s in skills if s and s not in pruned))
    if info["coursework"] is not None and plan["coursework"]:
        old = marked_text(ps[info["coursework"]])
        if "capstone" in old.lower() and "capstone" not in plan["coursework"].lower():
            plan["questions_for_rohan"].append("Coursework rewrite dropped the capstone line; kept the original.")
        else:
            change(
                "coursework",
                info["coursework"],
                "**Coursework: **" + re.sub(r"^\**Coursework:\**\s*", "", plan["coursework"]),
            )
    return changes
