"""Plan the tailoring for postings and cache the result; run after the digest so Tailor opens instantly.

python prepare.py            plans every Apply row of the latest run (cap in config: prepare_cap, default 20)
Also imported by server.py: make_tailor(job) and plan_cache_path(job)."""

import json
import re
import sys
from pathlib import Path

from docx import Document

from radar import digest
from tailoring import apply as applier
from tailoring import plan as planner
from tailoring import skills, tailor

sys.stdout.reconfigure(encoding="utf-8")
PLANS = Path(".cache/ui/plans")


def plan_cache_path(j):
    return PLANS / (re.sub(r"[^\w.-]+", "_", f"{j['company']}_{j['req_id']}") + ".json")


def row(j):
    v = j.get("verdict") or {}
    return {
        "key": f"{j['company']}|{j['req_id']}",
        "company": j["company"],
        "req_id": j["req_id"],
        "title": j["title"],
        "location": j.get("detail_location") or j["location"],
        "posted_on": j["posted_on"],
        "url": j["url"],
        "score_entry": v.get("score_entry"),
        "score_experienced": v.get("score_experienced"),
        "recommended_resume": v.get("recommended_resume"),
        "recommended_variant": v.get("recommended_variant"),
        "sponsorship": j.get("sponsorship"),
        "evidence": j.get("sponsorship_evidence") or v.get("sponsorship_evidence"),
        "why": v.get("why") or v.get("error"),
        "cover": v.get("cover_letter_required", False),
    }


def make_tailor(j):
    """Plan with --no-prompt semantics; return the base/tailored text per section for the editor."""
    profile = (
        Path("profile.md").read_text(encoding="utf-8")
        + "\n\nRULES:\n"
        + Path("docs/RESUME_RULES.md").read_text(encoding="utf-8")
    )
    base, base_label = applier.pick_base(j)
    doc = Document(base)
    info = tailor.parse(doc)
    plan = planner.make_plan(doc, info, j.get("description", ""), j, profile)
    planner.fix_summary(plan, doc, info, profile)
    if not applier.HEADLINE.match(plan["summary"]):
        plan["summary"] = f"**{plan['headline']}** " + plan["summary"]
    ps = doc.paragraphs
    before = {i: tailor.marked_text(ps[i]) for job in info["jobs"] for i in job["bullets"]}
    before.update(
        {
            info["summary"]: tailor.marked_text(ps[info["summary"]]),
            info["skills"]: tailor.marked_text(ps[info["skills"]]),
        }
    )
    if info["coursework"] is not None:
        before[info["coursework"]] = tailor.marked_text(ps[info["coursework"]])
    tailor.apply_plan(doc, info, plan, extra_allowed=skills.text())
    after = {i: tailor.marked_text(ps[i]) for i in before}
    notes = {}
    for h in plan["hard_to_defend"] + plan["questions_for_rohan"]:
        m = re.search(r"job (\d+) bullet (\d+)", h, re.I)
        notes.setdefault((int(m.group(1)), int(m.group(2))) if m else "general", []).append(h)
    secs = [{"id": "summary", "label": "Summary", "base": [before[info["summary"]]], "text": [after[info["summary"]]]}]
    for k, job in enumerate(info["jobs"]):
        order = next((pj["order"] for pj in plan["jobs"] if pj["job"] == k), list(range(len(job["bullets"]))))
        order = order if sorted(order) == list(range(len(job["bullets"]))) else list(range(len(job["bullets"])))
        secs.append(
            {
                "id": f"job{k}",
                "label": ps[job["header"]].text.split("\t")[0].strip(),
                "order": order,
                "base": [before[i] for i in job["bullets"]],
                "text": [after[job["bullets"][i]] for i in order],
                "moved": [order[n] != n for n in range(len(order))],
                "notes": {str(n): notes.get((k, order[n]), []) for n in range(len(order))},
            }
        )
    secs.append({"id": "skills", "label": "Skills", "base": [before[info["skills"]]], "text": [after[info["skills"]]]})
    if info["coursework"] is not None:
        secs.append(
            {
                "id": "coursework",
                "label": "Coursework",
                "base": [before[info["coursework"]]],
                "text": [after[info["coursework"]]],
            }
        )
    skip, lines = applier.assess(j)
    return {
        "job": row(j),
        "base": str(base),
        "base_label": base_label,
        "headline": plan["headline"],
        "skip": skip,
        "assessment": lines,
        "years_required": j.get("years_required"),
        "platform_tools": (j.get("verdict") or {}).get("platform_tools_missing", []),
        "jd_skills": plan.get("jd_skills_not_confirmed", []),
        "general_notes": notes.get("general", []),
        "sections": secs,
        "fit_notes": plan.get("fit_notes", ""),
    }


def main():
    cfg = json.load(open("config.json", encoding="utf-8"))
    cap = cfg.get("prepare_cap", 20)
    run = json.loads(Path("last_run.json").read_text(encoding="utf-8")) if Path("last_run.json").exists() else {}
    new = [j for j in digest.load_jsonl("jobs.jsonl") if j.get("first_seen") == run.get("ran_at")]
    todo = [j for j in digest.sections(new)["apply"] if not plan_cache_path(j).exists()][:cap]
    print(f"preparing plans for {len(todo)} Apply postings (cap {cap})")
    PLANS.mkdir(parents=True, exist_ok=True)
    for j in todo:
        try:
            plan_cache_path(j).write_text(json.dumps(make_tailor(j)), encoding="utf-8")
            print(f"  planned {j['company']} | {j['title'][:50]}", flush=True)
        except Exception as e:  # one failure must not stop the others; Tailor will plan it on demand
            print(f"  ! {j['company']} | {j['title'][:50]}: {str(e)[:120]}", flush=True)


if __name__ == "__main__":
    main()
