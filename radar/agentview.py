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
        + ([f"Already {rec['done'].replace(' ', ' on ', 1)}."] if rec.get("done") else [])
        + [f'Find them on LinkedIn: search "{d["search_hint"]}"', "", "LinkedIn note:", d["linkedin_note"], ""]
        + [f"Email subject: {d['email_subject']}", d["email_body"]]
        + notes(rec)
    )


def news(since):
    """What the writing agents made since a time ("%Y-%m-%d %H:%M"), as short lines for the morning brief."""
    out = [f"Interview prep ready: {p['company']}, {p['title']}" for p in prep.report()["items"] if p["made"] >= since]
    drafts = [d for d in followup.report()["items"] if d["made"] >= since]
    if drafts:
        names = ", ".join(sorted({d["company"] for d in drafts})[:4])
        out.append(f"{len(drafts)} follow-up draft{'s' if len(drafts) > 1 else ''} ready: {names}")
    return out


def text(name, company=None, req_id=None):
    """Everything one writer made, one employer's (its exact name, any case), or one application's. One
    application's shows even after its draft was marked sent, so asking for it again never pays for another."""
    mod = prep if name == "prep" else followup
    if company and req_id:
        rec = mod.load().get(f"{company}|{req_id}")
        items = [dict(rec, key=f"{company}|{req_id}")] if rec else []
    else:
        typed = (company or "").strip().lower()
        items = [r for r in mod.report()["items"] if not typed or r["company"].lower() == typed]
    if not items:
        return "nothing written yet" + (f" for {company}" if company else "")
    page = prep_text if name == "prep" else followup_text
    return "\n\n----\n\n".join(page(r) for r in items)
