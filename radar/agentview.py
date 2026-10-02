"""What the writing agents made, as plain pages for the terminal (python -m radar.agents show) and the assistant."""

from radar import followup, prep


def notes(rec):
    return ["", "Notes:"] + [f"- {n}" for n in rec["notes"]] if rec.get("notes") else []


def prep_text(rec):
    p = rec["prep"]
    stage = {"screen": "recruiter screen", "interview": "interview"}.get(rec["stage"], "first screen")
    out = [f"Interview prep: {rec['title']} at {rec['company']}, for the {stage}, made {rec['made']}", ""]
    out += [p["role"], "", "What they will probe:"]
    out += [
        f"- {f['topic']}: {f['why']} Your evidence: {f['evidence'] or 'nothing on the resume yet.'}" for f in p["focus"]
    ]
    out += ["", "Likely questions:"]
    out += [f"{i}. {q['question']} ({q['kind']}) {q['answer_from']}" for i, q in enumerate(p["questions"], 1)]
    out += ["", "Stories:"]
    for s in p["stories"]:
        out += [f"- {s['title']}"] + [f"  {k.title()}: {s[k]}" for k in ("situation", "task", "action", "result")]
    if p["gaps"]:
        out += ["", "Gaps, and how to answer them:"] + [f"- {g['gap'].rstrip('.')}: {g['answer']}" for g in p["gaps"]]
    out += ["", "Ask them:"] + [f"- {q}" for q in p["ask_them"]]
    return "\n".join(out + ["", "Work authorization:", p["work_authorization"]] + notes(rec))


def followup_text(rec):
    d = rec["draft"]
    return "\n".join(
        [f"Follow-up: {rec['title']} at {rec['company']}, applied {rec['applied']}"]
        + [f'Find them on LinkedIn: search "{d["search_hint"]}"', "", "LinkedIn note:", d["linkedin_note"], ""]
        + [f"Email subject: {d['email_subject']}", d["email_body"]]
        + notes(rec)
    )


def text(name, company=None):
    """Everything one writer made, or one employer's part of it."""
    items = (prep if name == "prep" else followup).report()["items"]
    items = [r for r in items if not company or company.lower() in r["company"].lower()]
    if not items:
        return "nothing written yet" + (f" for {company}" if company else "")
    page = prep_text if name == "prep" else followup_text
    return "\n\n----\n\n".join(page(r) for r in items)
