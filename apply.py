"""apply.py <company> <req_id> [--cover] [--outreach] [--force] [--yes]: tailor a resume for one posting.

Reads RESUME_RULES.md conventions: assess fit first, start from the recommended base/variant, lock facts,
show before/after for approval, then build Resume/For <Company>/<req_id>_<short-title>/."""
import argparse
import json
import re
import shutil
import sys
from pathlib import Path

from docx import Document

import letters
import plan as planner
import resumes
import skills
import tailor

sys.stdout.reconfigure(encoding="utf-8")
OVERLAPS = ["Kridha ran concurrently with StackNexus (part-time consulting alongside the full-time role).",
            "The two AREC roles overlapped (research assistantship continued while the data engineering scope grew).",
            "The two Adventaus roles overlapped (promoted from Data Engineer to Data Scientist on the same client)."]
HEADLINE = re.compile(r"^(?:\*\*)?(Data Engineer|Data Scientist|ML Engineer|Machine Learning Engineer|AI Engineer)")


def find_job(company, req_id):
    for line in Path("jobs.jsonl").read_text(encoding="utf-8").splitlines():
        j = json.loads(line)
        if j["company"].lower() == company.lower() and j["req_id"].lower() == req_id.lower():
            return j
    sys.exit(f"no posting {company} {req_id} in jobs.jsonl")


def assess(j):
    """Honest fit check before anything is touched. Returns (skip, lines)."""
    v, lines, skip = j.get("verdict") or {}, [], False
    if j.get("sponsorship") in ("no", "perm_ad"):
        skip = True
        lines.append(f"SKIP: sponsorship={j['sponsorship']}: \"{j.get('sponsorship_evidence')}\"")
    elif j.get("sponsorship") == "unlikely":
        lines.append("WARN: company default says no sponsorship; posting text is silent")
    if j.get("years_gate"):
        skip = True
        lines.append(f"SKIP: years gate, {j.get('years_required')}+ years required")
    if v.get("platform_tools_missing"):
        lines.append("WARN: platform tools required that Rohan lacks: " + ", ".join(v["platform_tools_missing"]))
    if v.get("hard_requirements_missing"):
        lines.append("missing: " + "; ".join(v["hard_requirements_missing"]))
    lines.append(f"scores entry {v.get('score_entry')} / experienced {v.get('score_experienced')}; model apply={v.get('apply')}")
    return skip, lines


def ensure_variant(role, variant):
    """Create an empty role's variant by copying the DS and DE variant of the same length (headline rotated later)."""
    path = resumes.variant_path(role, variant)
    if not path.exists():
        src = resumes.variant_path("DS and DE Resumes", variant)
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(src, path)
        print(f"created {path} from {src}")
    return path


def pick_base(j):
    v = j.get("verdict") or {}
    if v.get("recommended_resume") == "entry":
        return resumes.ENTRY_BASE, "entry"
    role, _, variant = (v.get("recommended_variant") or "DS and DE Resumes/two-page").partition("/")
    if role not in resumes.role_folders() or variant not in resumes.VARIANT_DIRS:
        role, variant = "DS and DE Resumes", "two-page"
    return ensure_variant(role, variant), f"experienced {role}/{variant}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("company"); ap.add_argument("req_id")
    ap.add_argument("--cover", action="store_true"); ap.add_argument("--outreach", action="store_true")
    ap.add_argument("--force", action="store_true"); ap.add_argument("--yes", action="store_true")
    ap.add_argument("--no-prompt", action="store_true", help="never ask JD-skill y/n; write them to notes.md instead")
    a = ap.parse_args()
    rules = Path("RESUME_RULES.md").read_text(encoding="utf-8")
    profile = Path("profile.md").read_text(encoding="utf-8")
    j = find_job(a.company, a.req_id)
    skip, lines = assess(j)
    print("\n".join(lines))
    if skip and not a.force:
        sys.exit("Fit assessment says skip. Pass --force to tailor anyway.")

    base, base_label = pick_base(j)
    short = re.sub(r"[^A-Za-z0-9]+", "-", j["title"]).strip("-")[:40]
    folder = resumes.ROOT / f"For {j['company']}" / f"{j['req_id']}_{short}"
    folder.mkdir(parents=True, exist_ok=True)
    jd = j.get("description", "")
    (folder / "jd.txt").write_text(f"{j['title']} at {j['company']}\n{j['url']}\n\n{jd}", encoding="utf-8")

    doc = Document(base)
    info = tailor.parse(doc)
    plan = planner.make_plan(doc, info, jd, j, profile + "\n\nRULES:\n" + rules)
    accepted, declined, deferred = skills.confirm(plan.get("jd_skills_not_confirmed", []), allow_prompt=not a.no_prompt)
    if accepted:  # newly confirmed skills may now be used: re-plan once
        plan = planner.make_plan(doc, info, jd, j, profile + "\n\nRULES:\n" + rules)
    skill_notes = [f"JD asks for {s}: confirmed, added to skills_confirmed.md" for s in accepted]
    skill_notes += [f"JD asks for {s}: not used, left out (gap to acknowledge if asked)" for s in declined]
    skill_notes += [f"JD asks for {s}. Have you used it? [y/n] (unattended run: answer by adding it to "
                    f"skills_confirmed.md and rerunning)" for s in deferred]
    planner.fix_summary(plan, doc, info, profile)
    if not HEADLINE.match(plan["summary"]):
        plan["summary"] = f"**{plan['headline']}** " + plan["summary"]
    changes = tailor.apply_plan(doc, info, plan, extra_allowed=skills.text())
    print(f"\nbase: {base_label} ({base})\n{len(changes)} changes:")
    for where, before, after in changes:
        print(f"\n[{where}]\n  BEFORE: {before}\n  AFTER:  {after}")
    if not a.yes and input("\nBuild the docx with these changes? [y/N] ").strip().lower() != "y":
        sys.exit("not built")

    out = folder / f"Resume - Siddhi Rohan ({plan['headline']}).docx"
    doc.save(out)
    notes = [f"# {j['title']} at {j['company']} ({j['req_id']})", "", j["url"], "", "## Fit assessment", ""]
    notes += [f"- {l}" for l in lines] + ["", f"- base used: {base_label}", f"- headline: {plan['headline']}",
                                          f"- {plan['fit_notes']}", "", "## Changes (before / after)", ""]
    for where, before, after in changes:
        notes += [f"### {where}", "", f"BEFORE: {before}", "", f"AFTER: {after}", ""]
    notes += ["## Hard to defend", ""] + ([f"- {x}" for x in plan["hard_to_defend"]] or ["- none"])
    notes += ["", "## JD skills outside skills_confirmed.md", ""] + ([f"- {s}" for s in skill_notes] or ["- none"])
    notes += ["", "## Questions for Rohan (nothing below went into the resume)", ""]
    notes += [f"- {q}" for q in plan["questions_for_rohan"]] or ["- none"]
    notes += ["", "## Date overlap explanations", ""] + [f"- {o}" for o in OVERLAPS]
    v = j.get("verdict") or {}
    if a.cover or v.get("cover_letter_required"):
        text = letters.cover_letter(j, jd, profile, resumes.docx_text(out))
        letters.write_docx(text, folder / "cover_letter.docx", base)
        notes += ["", "## Cover letter", "", text]
    if a.outreach:
        o = letters.outreach(j, jd, profile, resumes.docx_text(out))
        (folder / "outreach.md").write_text(f"# Outreach\n\n## LinkedIn note ({len(o['linkedin_note'])} chars)\n\n"
                                            f"{o['linkedin_note']}\n\n## Message ({len(o['message'].split())} words)\n\n"
                                            f"{o['message']}\n", encoding="utf-8")
    (folder / "notes.md").write_text("\n".join(notes) + "\n", encoding="utf-8")
    print(f"\nbuilt {out}\nnotes: {folder / 'notes.md'}\nnext: python finalize.py \"{folder}\"")


if __name__ == "__main__":
    main()
