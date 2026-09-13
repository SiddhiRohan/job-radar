"""Ask Claude for a tailoring plan; re-ask for the summary if it drifts beyond the base resume's vocabulary."""
import re

import llm
import skills
import tailor

PLAN_SCHEMA = {"type": "object", "additionalProperties": False, "properties": {
    "headline": {"type": "string", "enum": ["Data Engineer", "Data Scientist", "ML Engineer", "AI Engineer"]},
    "summary": {"type": "string"},
    "jobs": {"type": "array", "items": {"type": "object", "additionalProperties": False, "properties": {
        "job": {"type": "integer"}, "order": {"type": "array", "items": {"type": "integer"}},
        "rewrites": {"type": "array", "items": {"type": "object", "additionalProperties": False, "properties": {
            "bullet": {"type": "integer"}, "text": {"type": "string"}, "reason": {"type": "string"}},
            "required": ["bullet", "text", "reason"]}}}, "required": ["job", "order", "rewrites"]}},
    "skills": {"type": "string"}, "coursework": {"type": "string"},
    "jd_skills_not_confirmed": {"type": "array", "items": {"type": "string"}},
    "hard_to_defend": {"type": "array", "items": {"type": "string"}},
    "questions_for_rohan": {"type": "array", "items": {"type": "string"}},
    "fit_notes": {"type": "string"}},
    "required": ["headline", "summary", "jobs", "skills", "coursework", "jd_skills_not_confirmed", "hard_to_defend",
                 "questions_for_rohan", "fit_notes"]}

PLAN_RULES = """You tailor a resume to one job posting. LOCKED: employer names, titles, dates, GPA, every number.
Allowed, phrased to mirror the posting: freely reword the summary; reorder and reword bullets within a job; edit the
Skills line. The vocabulary you may draw on is the base resume text plus the CONFIRMED SKILLS list (everything the
candidate has actually used). Do not introduce tools or experience outside that vocabulary. When the posting asks for
a skill that is outside it, do NOT use it; list it in jd_skills_not_confirmed (short names, e.g. "Databricks").
Keep **bold** markers on methods, domain terms, and headline metrics; use ** in your text the same way. Keep the
Coursework label and the capstone note. Never use em dashes. Defensibility: if a rewrite overstates depth on a
confirmed skill (for example "led" where the base says "supported", or "production" where the base says "prototype"),
either soften it or list it in hard_to_defend. Return only text for bullets you actually change.
Headline rotates by role: Data Engineer, Data Scientist, ML Engineer, AI Engineer."""

SUMMARY_SCHEMA = {"type": "object", "additionalProperties": False, "properties": {"summary": {"type": "string"}},
                  "required": ["summary"]}


def make_plan(doc, info, jd_text, job_meta, profile):
    ps = doc.paragraphs
    blocks = [f"SUMMARY: {tailor.marked_text(ps[info['summary']])}"]
    for k, j in enumerate(info["jobs"]):
        blocks.append(f"JOB {k}: {ps[j['header']].text.strip()}")
        blocks += [f"  bullet {b}: {tailor.marked_text(ps[i])}" for b, i in enumerate(j["bullets"])]
    blocks.append(f"SKILLS: {ps[info['skills']].text.strip()}")
    if info["coursework"] is not None:
        blocks.append(f"COURSEWORK: {ps[info['coursework']].text.strip()}")
    user = (f"POSTING: {job_meta['title']} at {job_meta['company']}\n{jd_text[:12000]}\n\nBASE RESUME:\n"
            + "\n".join(blocks) + "\n\nCONFIRMED SKILLS:\n" + ", ".join(skills.load()) + "\n\nReturn the tailoring plan.")
    return llm.complete(PLAN_RULES + "\n\nCANDIDATE PROFILE:\n" + profile, user, PLAN_SCHEMA, max_tokens=6000)[0]


def fix_summary(plan, doc, info, profile):
    """One constrained retry when the summary uses terms outside base + confirmed skills; else the base summary."""
    ps = doc.paragraphs
    base_text = "\n".join(p.text for p in ps) + "\nCONFIRMED SKILLS: " + ", ".join(skills.load())
    bad = tailor.new_terms(plan["summary"], base_text.lower())
    if not bad:
        return
    base_summary = tailor.marked_text(ps[info["summary"]])
    user = (f"BASE SUMMARY: {base_summary}\nPROPOSED SUMMARY: {plan['summary']}\nThe proposed summary uses terms that "
            f"appear neither on the base resume nor in the confirmed skills: {', '.join(bad)}. Rewrite it using ONLY "
            f"the vocabulary below, keeping the headline '{plan['headline']}' first and **bold** "
            f"markers.\n\nBASE RESUME TEXT:\n{base_text[:9000]}")
    out, _ = llm.complete(PLAN_RULES + "\n\nCANDIDATE PROFILE:\n" + profile, user, SUMMARY_SCHEMA)
    still = tailor.new_terms(out["summary"], base_text.lower())
    if still:
        plan["questions_for_rohan"].append(f"Summary retry still used unsupported terms ({', '.join(still)}); kept the "
                                           f"base summary with the headline rotated. Proposed: {out['summary']}")
        plan["summary"] = re.sub(r"^(\*\*)?[A-Za-z ]+?(?= with )", f"**{plan['headline']}**", base_summary, count=1)
    else:
        plan["questions_for_rohan"].append(f"Summary was rewritten once to drop unsupported terms ({', '.join(bad)}).")
        plan["summary"] = out["summary"]
