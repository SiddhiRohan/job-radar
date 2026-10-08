"""What the writing agents made, as plain pages for the terminal (python -m radar.agents show) and the assistant."""

from radar import audit, debrief, dropped, followup, prep, scout


def notes(rec):
    return ["", "Notes:"] + [f"- {n}" for n in rec["notes"]] if rec.get("notes") else []


def audit_text(r):
    """The latest filter audit, or what the rules dropped this week when there is none yet."""
    week = ", ".join(f"{n} {dropped.LABELS.get(k, k)}" for k, n in sorted(r["dropped"].items(), key=lambda kv: -kv[1]))
    if not r.get("made"):
        return "No filter audit yet. Dropped in the last week: " + (week or "nothing logged yet") + "."
    out = [f"Filter audit, {r['made']}, of what the rules dropped since {r['since']}", "", r["summary"]]
    if r["wanted"]:
        out += ["", "Dropped, but probably worth seeing:"]
        out += [f"- {w['company']}, {w['title']} ({w['reason']}, {w['count']}): {w['why']}" for w in r["wanted"]]
    if r["changes"]:
        out += ["", "Changes that would have kept them (python -m radar.agents audit apply N):"]
        for n, c in enumerate(r["changes"], 1):
            done = " Applied." if n - 1 in (r["applied"] or []) else ""
            out.append(f'{n}. {c["setting"]}: {c["action"]} "{c["value"]}". {c["why"]}{done}')
    return "\n".join(out + notes(r))


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


def debrief_text(rec):
    d = rec["debrief"]
    out = [f"Interview debrief: {rec['title']} at {rec['company']}, the {rec['stage']} on {rec['added'][:10]}", ""]
    out += [d["summary"], "", "What they asked:"]
    for i, a in enumerate(d["asked"], 1):
        out.append(f"{i}. {a['question']} ({a['went']})" + (f" Try saying: {a['better']}" if a["better"] else ""))
    if d["concerns"]:
        out += ["", "They seemed unsure about:"] + [
            f"- {c['concern'].rstrip('.')}: {c['address']}" for c in d["concerns"]
        ]
    out += ["", "Keep doing:"] + [f"- {x}" for x in d["went_well"]]
    out += ["", "For the next round:"] + [f"- {x}" for x in d["next_round"]]
    if d["owed"]:
        out += ["", "You said you would send:"] + [f"- {x}" for x in d["owed"]]
    return "\n".join(out + ["", f"Thank-you note: {d['thank_you_subject']}", d["thank_you_body"]] + notes(rec))


PAGES = {"prep": (prep, prep_text), "followups": (followup, followup_text), "debrief": (debrief, debrief_text)}


def news(since):
    """What the writing agents made after a time ("%Y-%m-%d %H:%M"), as short lines for the morning brief. After, not
    from: the run writes its drafts and then its brief, often in the same minute, and those drafts were announced."""
    out = [f"Interview prep ready: {p['company']}, {p['title']}" for p in prep.report()["items"] if p["made"] > since]
    drafts = [d for d in followup.report()["items"] if d["made"] > since]
    if drafts:
        names = ", ".join(sorted({d["company"] for d in drafts})[:4])
        out.append(f"{len(drafts)} follow-up draft{'s' if len(drafts) > 1 else ''} ready: {names}")
    out += [
        f"Interview debrief ready: {d['company']}, {d['title']}" for d in debrief.report()["items"] if d["made"] > since
    ]
    found = [f["name"] for f in scout.report()["found"] if (f.get("checked") or "") > since[:10]]
    if found:
        out.append("Company scout found: " + ", ".join(found[:4]) + (" and more" if len(found) > 4 else ""))
    a = audit.report()
    if (a.get("made") or "") > since:
        out.append(
            f"Filter audit: {len(a['wanted'])} dropped posting(s) worth a look, {len(a['changes'])} change(s) to try"
        )
    return out


def text(name, company=None, req_id=None):
    """Everything one writer made, one employer's (its exact name, any case), or one application's. One
    application's shows even after its draft was marked sent, so asking for it again never pays for another; a
    debrief keeps every round, so all of an application's rounds show, newest first. The audit has one page."""
    if name == "audit":
        return audit_text(audit.report())
    mod, page = PAGES[name]
    if company and req_id and name != "debrief":
        rec = mod.load().get(f"{company}|{req_id}")
        items = [dict(rec, key=f"{company}|{req_id}")] if rec else []
    else:
        typed = (company or "").strip().lower()
        items = [r for r in mod.report()["items"] if not typed or r["company"].lower() == typed]
        items = [r for r in items if not req_id or r["req_id"] == req_id]
    if not items:
        return "nothing written yet" + (f" for {company}" if company else "")
    return "\n\n----\n\n".join(page(r) for r in items)
