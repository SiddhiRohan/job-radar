"""Ask Claude for a tailoring plan; re-ask for the summary if it drifts beyond the base resume's vocabulary."""
import re

import llm
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
    "hard_to_defend": {"type": "array", "items": {"type": "string"}},
    "questions_for_rohan": {"type": "array", "items": {"type": "string"}},
    "fit_notes": {"type": "string"}},
    "required": ["headline", "summary", "jobs", "skills", "coursework", "hard_to_defend", "questions_for_rohan", "fit_notes"]}

PLAN_RULES = """You tailor a resume to one job posting. LOCKED: header, employer names, titles, dates, GPA, every number.
Allowed: rewrite the summary to mirror the posting's phrasing USING ONLY skills, tools, and experience that already
appear on the base resume; reorder bullets within a job by relevance; lightly reword bullets to mirror the posting's
terms WITHOUT adding tools, scope, or facts not already in the base; adjust the Skills line (only tools already on the
base resume, reordered or pruned); pick coursework already listed (keep the Coursework label and the capstone note).
Keep **bold** markers on methods, domain terms, and headline metrics; use ** in your text the same way.
Never use em dashes. If a bullet would need something new to match the posting, put a question in questions_for_rohan
instead of writing it. Flag bullets that would be hard to defend in an interview. Return only text for bullets you
actually change; keep rewrites minimal. Headline rotates by role: Data Engineer, Data Scientist, ML Engineer, AI Engineer."""

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
            + "\n".join(blocks) + "\n\nReturn the tailoring plan.")
    return llm.complete(PLAN_RULES + "\n\nCANDIDATE PROFILE:\n" + profile, user, PLAN_SCHEMA, max_tokens=6000)[0]


def fix_summary(plan, doc, info, profile):
    """One constrained retry when the summary uses terms absent from the base; else fall back to the base summary."""
    ps = doc.paragraphs
    base_text = "\n".join(p.text for p in ps)
    bad = tailor.new_terms(plan["summary"], base_text.lower())
    if not bad:
        return
    base_summary = tailor.marked_text(ps[info["summary"]])
    user = (f"BASE SUMMARY: {base_summary}\nPROPOSED SUMMARY: {plan['summary']}\nThe proposed summary uses terms that "
            f"appear nowhere on the base resume: {', '.join(bad)}. Rewrite it using ONLY skills, tools, and experience "
            f"that appear in the base resume text below, keeping the headline '{plan['headline']}' first and **bold** "
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
