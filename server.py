"""python server.py: FastAPI on localhost:8000 wrapping the radar modules for the web UI. No logic is duplicated here."""

import json
import os
import re
import shutil
import threading
import uuid
import webbrowser
from pathlib import Path
from urllib.parse import urlparse

import uvicorn
from docx import Document
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from radar import (
    agents,
    applications,
    audit,
    autorun,
    brief,
    chat,
    debrief,
    digest,
    doctor,
    evaluate,
    factors,
    firstrun,
    followup,
    gaps,
    mail,
    owner,
    patterns,
    prep,
    prepare,
    salary,
    schedule,
    scout,
    sponsormap,
    watch,
)
from tailoring import apply as applier
from tailoring import finalize, letters, resumes, skills, tailor

app = FastAPI()
JOBS, JOB_LOCK = {}, threading.Lock()
UI_DIR = Path(".cache/ui")


def jobs_all():
    return digest.load_jsonl("jobs.jsonl")


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
        "salary": salary.extract(j.get("description", "")),
        "factors": factors.table(j),  # [] for verdicts stored before factors existed
    }


def background(fn, *args):
    job_id = uuid.uuid4().hex[:10]
    JOBS[job_id] = {"status": "running"}

    def run():
        try:
            JOBS[job_id] = {"status": "done", "result": fn(*args)}
        except Exception as e:  # surfaced to the page as text; never swallowed
            import traceback

            where = traceback.extract_tb(e.__traceback__)[-1]
            JOBS[job_id] = {
                "status": "error",
                "error": f"{type(e).__name__}: {str(e)[:300]} ({where.filename.split(chr(92))[-1]}:{where.lineno})",
            }

    threading.Thread(target=run, daemon=True).start()
    return {"job_id": job_id}


@app.get("/jobs/{job_id}")
def job_status(job_id):
    return JOBS.get(job_id) or {
        "status": "error",
        "error": "unknown job id; the server may have restarted, reload the page",
    }


@app.get("/api/dates")
def dates():
    return sorted({j.get("first_seen", "")[:10] for j in jobs_all() if j.get("first_seen")}, reverse=True)


@app.get("/api/today")
def today(date: str = ""):
    all_jobs = jobs_all()
    date = date or (dates()[0] if dates() else "")
    new = [j for j in all_jobs if j.get("first_seen", "")[:10] == date]
    run = json.loads(Path("last_run.json").read_text(encoding="utf-8")) if Path("last_run.json").exists() else {}
    stats = None
    if run.get("ran_at", "")[:10] == date:
        removed = run.get("removed") or {}
        top = max(removed, key=removed.get) if removed else None
        stats = (
            f"Polled {run.get('companies_polled')} companies, kept {len(new)}, removed "
            f"{sum(removed.values())} by rule" + (f" ({removed[top]} {top.replace('_', ' ')})." if top else ".")
        )
    s = digest.sections(new)
    done = {r["req_id"] + "|" + r["company"] for r in applied_rows()}
    out = {k: [dict(row(j), applied=(j["req_id"] + "|" + j["company"]) in done) for j in v] for k, v in s.items()}
    for k in out:
        out[k].sort(
            key=lambda r: (
                -max([x for x in (r["score_entry"], r["score_experienced"]) if isinstance(x, int)] or [0]),
                r["company"],
            )
        )
    return {"date": date, "dates": dates(), "stats": stats, "sections": out}


def applied_rows():
    return applications.rows()


def write_applied(rows):
    applications.write(rows)


@app.get("/api/posting")
def posting(company: str, req_id: str):
    """One stored posting with its description, for the drawer: the row fields plus the text and what to highlight."""
    j = next((x for x in jobs_all() if x["company"] == company and x["req_id"] == req_id), None)
    if j is None:
        raise HTTPException(404, "posting not stored")
    text = j.get("description", "")
    return row(j) | {
        "description": text,
        "years_required": j.get("years_required"),
        "pay_sentence": salary.sentence(text),
    }


@app.get("/api/applied")
def applied():
    """Applications, newest first, each with its posting URL from jobs.jsonl so the page can link it."""
    urls = {f"{j['company']}|{j['req_id']}": j.get("url") for j in jobs_all()}
    rows = [dict(r, url=urls.get(f"{r['company']}|{r['req_id']}")) for r in applied_rows()]
    return sorted(rows, key=lambda r: r["date"], reverse=True)


@app.post("/api/applied")
def mark_applied(body: dict):
    if not applications.add(body["company"], body["req_id"], body["title"], body.get("folder", "")):
        return {"ok": True, "already": True}
    return {"ok": True}


@app.post("/api/applied/undo")
def undo_applied(body: dict):
    """Take a mistaken click back. Refused once an email has moved the application past "applied"."""
    gone = applications.remove(body["company"], body["req_id"])
    if gone is None:
        raise HTTPException(409, "This application has moved past applied, so it stays; change its status on Applied")
    return {"ok": True}


@app.post("/api/applied/status")
def set_status(body: dict):
    rows = applied_rows()
    for r in rows:
        if r["req_id"] == body["req_id"] and r["company"] == body["company"]:
            r["status"] = body["status"] if body["status"] in applications.STATUSES else r["status"]
            if body.get("folder") is not None:
                r["folder"] = body["folder"]
    write_applied(rows)
    return {"ok": True}


@app.get("/api/patterns")
def rejection_patterns():
    """Where the rejections cluster, from applications.md joined with the stored postings."""
    return patterns.analyse()


@app.get("/api/watch")
def posting_watch():
    """Closed and changed postings behind open applications, from the last watch run."""
    return watch.report()


@app.post("/api/watch/run")
def posting_watch_run():
    return background(lambda: watch.run() | watch.report())


@app.get("/api/agents")
def agent_reports():
    """What the agents wrote and found: interview prep, follow-up drafts, skill gaps and the sponsor map."""
    jobs, cfg = jobs_all(), agents.config()
    return {
        "key": agents.has_key(),
        "waiting": agents.waiting(cfg),
        "followup_after_days": (cfg.get("agents") or {}).get("followup_after_days", followup.AFTER_DAYS),
        "prep": prep.report(),
        "debriefs": debrief.report(),
        "audit": audit.report(),
        "scout": scout.report(),
        "followups": followup.report(),
        "gaps": gaps.analyse(jobs),
        "sponsors": sponsormap.analyse(jobs),
    }


@app.post("/api/agents/run")
def agent_run(body: dict):
    """Write what is due now, or with a company, that employer's prep or follow-up. Refused without an API key or
    while the morning run is going, since its own agents step is about to write the same things."""
    if why := agents.refuse():
        raise HTTPException(409, why)
    who = (body["company"], body.get("req_id")) if body.get("company") else None
    return background(agents.run, [body["name"]] if body.get("name") else None, who)


@app.post("/api/agents/debrief")
def debrief_add(body: dict):
    """Keep their account of an interview, then write its debrief; with no API key it is kept and waits."""
    company, req_id = body.get("company", ""), body.get("req_id", "")
    if not debrief.add(company, req_id, body.get("account", "")):
        raise HTTPException(400, "pick an application and say how it went")
    if why := agents.refuse():
        return {"kept": True, "note": why}
    return background(agents.run, ["debrief"], (company, req_id))


@app.post("/api/agents/audit/run")
def audit_run():
    """Write the filter audit now instead of waiting for the week to pass."""
    if why := agents.refuse():
        raise HTTPException(409, why)
    return background(agents.run, ["audit"], ("", None))


@app.post("/api/agents/audit/apply")
def audit_apply(body: dict):
    """Make one change the audit suggested, because the person pressed Apply."""
    return {"result": audit.apply(int(body.get("n", -1)))}


@app.post("/api/scout/run")
def scout_run():
    """Check the next few leads now. No model, but not during the morning run, which checks them itself."""
    if agents.runlock.held():
        raise HTTPException(409, "The morning run is going; it checks leads itself.")
    return background(scout.check, agents.config())


@app.post("/api/scout/decide")
def scout_decide(body: dict):
    """Follow a found employer, which adds it to companies.json, or skip it."""
    return scout.decide(body.get("name", ""), "follow" if body.get("how") == "follow" else "skip")


@app.post("/api/agents/followups/done")
def followup_done(body: dict):
    if not followup.done(body.get("key", ""), body.get("how", "sent")):
        raise HTTPException(404, "no such follow-up draft")
    return {"ok": True}


@app.get("/api/mail")
def mail_state():
    """Whether Gmail is set up, when it was last read, the needs-review list, and recent status updates."""
    s = mail.load()
    configured = bool(mail.env("GMAIL_ADDRESS") and mail.env("GMAIL_APP_PASSWORD"))
    return {
        "configured": configured,
        "last_sync": s["last_sync"],
        "review": s["review"],
        "events": s["events"][-8:][::-1],
        "untracked": s["untracked"][::-1],
    }


@app.post("/api/mail/sync")
def mail_sync():
    return background(mail.sync)


@app.post("/api/mail/unresolve")
def mail_unresolve(body: dict):
    return mail.unresolve(body["message_id"])


@app.post("/api/mail/resolve")
def mail_resolve(body: dict):
    return mail.resolve(body["message_id"], body.get("company"), body.get("req_id"), body.get("status"))


def check_mail_for(args):
    """Chat hook: read mail now and report what moved and what waits for review, without the email text."""
    result = mail.sync()
    review = [
        {k: r.get(k) for k in ("sender", "subject", "status", "company", "reason")} for r in mail.load()["review"]
    ]
    return result | {"needs_review": review[:8], "needs_review_total": len(review)}


@app.post("/api/pick-folder")
def pick_folder(body: dict):
    """Native folder dialog on this machine (the server is local); returns the chosen path or null if cancelled."""
    from tkinter import Tk, filedialog

    root = Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    start = Path(body.get("start") or resumes.ROOT)
    chosen = filedialog.askdirectory(
        initialdir=str(start if start.exists() else Path.cwd()), title="Save tailored files into"
    )
    root.destroy()
    return {"path": chosen or None}


@app.post("/api/open")
def open_path(body: dict):
    p = Path(body["path"])
    if not p.exists():
        raise HTTPException(404, f"{p} does not exist on disk")
    os.startfile(str(p.resolve()))
    return {"ok": True}


@app.post("/api/tailor")
def start_tailor(body: dict):
    """Cached plan comes back at once; pass fresh=true to re-plan (also used after confirming a JD skill)."""

    def work():
        j = evaluate.ingest_url(body["url"]) if body.get("url") else applier.find_job(body["company"], body["req_id"])
        cache = prepare.plan_cache_path(j)
        if cache.exists() and not body.get("fresh"):
            return dict(json.loads(cache.read_text(encoding="utf-8")), cached=True)
        result = prepare.make_tailor(j)
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps(result), encoding="utf-8")
        return result

    return background(work)


@app.post("/api/tailor/confirm")
def confirm_skill(body: dict):
    if body.get("used"):
        skills.add(body["skill"])
    return {"ok": True}


def rebuild(state, edits, cover_text):
    """Regenerate the docx from the edited right column with tailor.set_text/reorder, then finalize. No new docx logic."""
    doc = Document(state["base"])
    info = tailor.parse(doc)
    ps = doc.paragraphs
    for sec in state["sections"]:
        e = edits.get(sec["id"]) or {}
        if sec["id"].startswith("job"):
            job = info["jobs"][int(sec["id"][3:])]
            order = e.get("order", sec["order"])
            for n, idx in enumerate(order):
                tailor.set_text(ps[job["bullets"][idx]], e.get("text", sec["text"])[n])
            tailor.reorder(doc, job, order)
        else:
            tailor.set_text(ps[info[sec["id"]]], e.get("text", sec["text"])[0])
    out_dir = UI_DIR / uuid.uuid4().hex[:8]
    out_dir.mkdir(parents=True, exist_ok=True)
    resume = out_dir / f"{owner.resume_stem()} ({state['headline']}).docx"
    doc.save(resume)
    report = []
    finalize.finalize_docx(resume, report)
    files = [resume.name]
    if cover_text:
        letters.write_docx(cover_text, out_dir / "cover_letter.docx", state["base"])
        finalize.finalize_docx(out_dir / "cover_letter.docx", report)
        files.append("cover_letter.docx")
    (out_dir / "jd.txt").write_text(
        f"{state['job']['title']} at {state['job']['company']}\n{state['job']['url']}\n", encoding="utf-8"
    )
    return {"dir": str(out_dir), "files": files, "report": report}


@app.post("/api/tailor/rebuild")
def start_rebuild(body: dict):
    return background(rebuild, body["state"], body.get("edits", {}), body.get("cover"))


@app.post("/api/tailor/cover")
def start_cover(body: dict):
    def work():
        j = applier.find_job(body["company"], body["req_id"])
        text = "\n".join(t for s in body["sections"] for t in s["text"])
        return {"text": letters.cover_letter(j, j.get("description", ""), resumes.profile_text(), text)}

    return background(work)


@app.post("/api/tailor/outreach")
def start_outreach(body: dict):
    def work():
        j = applier.find_job(body["company"], body["req_id"])
        text = "\n".join(t for s in body["sections"] for t in s["text"])
        return letters.outreach(j, j.get("description", ""), resumes.profile_text(), text)

    return background(work)


@app.get("/api/tailor/files/{build_id}/{name}")
def download(build_id: str, name: str):
    p = UI_DIR / build_id / name
    if not p.exists():
        raise HTTPException(404, "file not built yet; run Rebuild first")
    return FileResponse(p, filename=name)


@app.post("/api/tailor/save")
def save_folder(body: dict):
    src = Path(body["dir"])
    job = body["job"]
    short = re.sub(r"[^A-Za-z0-9]+", "-", job["title"]).strip("-")[:40]
    dest = (
        Path(body["dest"]) if body.get("dest") else resumes.ROOT / f"For {job['company']}" / f"{job['req_id']}_{short}"
    )
    dest.mkdir(parents=True, exist_ok=True)
    for p in src.iterdir():
        shutil.copy(p, dest / p.name)
    notes = [f"# {job['title']} at {job['company']} ({job['req_id']})", "", job["url"], "", "## Fit assessment", ""]
    notes += [f"- {x}" for x in body.get("assessment", [])] + ["", "## Notes and questions", ""]
    notes += [f"- {n}" for n in body.get("notes", [])] or ["- none"]
    (dest / "notes.md").write_text("\n".join(notes) + "\n", encoding="utf-8")
    if body.get("outreach") is not None:
        outreach = body["outreach"]
        note, message = outreach["linkedin_note"], outreach["message"]
        (dest / "outreach.md").write_text(
            f"## LinkedIn note ({len(note)} characters; under 300)\n\n{note}\n\n"
            f"## Outreach message ({len(message.split())} words; 100–120 inclusive)\n\n{message}\n",
            encoding="utf-8",
        )
    return {"folder": str(dest)}


BUILDS = {}  # key -> last build dir, so chat can save what it built


def plan_for(args):
    """Chat tool: plan (cached) and return a compact summary the assistant can relay."""
    j = applier.find_job(args["company"], args["req_id"])
    cache = prepare.plan_cache_path(j)
    if cache.exists() and not args.get("fresh"):
        st = json.loads(cache.read_text(encoding="utf-8"))
    else:
        st = prepare.make_tailor(j)
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps(st), encoding="utf-8")
    changes = []
    for sec in st["sections"]:
        for n, (b, t) in enumerate(
            zip([sec["base"][i] for i in sec.get("order", range(len(sec["base"])))], sec["text"])
        ):
            if b.strip() != t.strip():
                changes.append({"section": sec["id"], "index": n, "before": b[:300], "after": t[:300]})
    return {
        "assessment": st["assessment"],
        "skip": st["skip"],
        "base": st["base_label"],
        "headline": st["headline"],
        "jd_skills_not_confirmed": st["jd_skills"],
        "changes": changes[:25],
        "changed_count": len(changes),
        "notes": (
            st["general_notes"] + [n for s in st["sections"] for v in (s.get("notes") or {}).values() for n in v]
        )[:12],
    }


def build_for(args):
    j = applier.find_job(args["company"], args["req_id"])
    cache = prepare.plan_cache_path(j)
    if not cache.exists():
        return {"error": "no plan yet; call tailor_posting first"}
    st = json.loads(cache.read_text(encoding="utf-8"))
    out = rebuild(st, args.get("edits") or {}, None)
    BUILDS[f"{j['company']}|{j['req_id']}"] = out["dir"]
    bid = Path(out["dir"]).name
    return {
        "files": out["files"],
        "download": [f"http://localhost:8000/api/tailor/files/{bid}/{f}" for f in out["files"]],
        "finalize": [r for r in out["report"] if r.startswith("Resume")][:1],
    }


def save_for(args):
    j = applier.find_job(args["company"], args["req_id"])
    d = BUILDS.get(f"{j['company']}|{j['req_id']}")
    if not d:
        return {"error": "nothing built yet; call build_resume first"}
    st = json.loads(prepare.plan_cache_path(j).read_text(encoding="utf-8"))
    return save_folder(
        {
            "dir": d,
            "job": st["job"],
            "dest": args.get("dest"),
            "assessment": st["assessment"],
            "notes": st["general_notes"],
        }
    )


@app.post("/api/chat")
def chat_message(body: dict):
    hooks = {
        "mark_applied": mark_applied,
        "set_status": set_status,
        "applied_rows": applied_rows,
        "tailor_posting": plan_for,
        "build_resume": build_for,
        "save_resume": save_for,
        "check_mail": check_mail_for,
        "rejection_patterns": lambda args: {"lines": patterns.summary(patterns.analyse())},
        "posting_status": lambda args: watch.report(),
        "morning_brief": lambda args: {"text": brief.text(brief.current())},
    }
    return background(chat.message, body.get("session", "default"), body["text"], body.get("context", {}), hooks)


@app.get("/api/chat/sessions")
def chat_sessions():
    return chat.sessions()


@app.get("/api/chat/history")
def chat_history(session: str = "default"):
    return chat.transcript(session)


@app.post("/api/chat/reset")
def chat_reset(body: dict):
    chat.SESSIONS.pop(body.get("session", "default"), None)
    p = chat.CHAT_DIR / f"{body.get('session', 'default')}.json"
    if p.exists():
        p.unlink()
    return {"ok": True}


@app.get("/api/brief")
def morning_brief():
    """The brief the last run wrote, or one built now when no run has written a complete one yet."""
    return brief.current()


@app.get("/api/setup")
def setup_state():
    """Resume, key and profile status for the setup page. The key itself is never sent back."""
    return firstrun.state() | {"checks": doctor.checks()}


@app.post("/api/setup/resume")
def setup_resume(body: dict):
    try:
        return {"ok": True, "saved": firstrun.save_resume(body.get("name"), body.get("data", ""))}
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


@app.post("/api/setup/key")
def setup_key(body: dict):
    try:
        return {"ok": True, "checked": firstrun.save_key(body.get("key"))}
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


@app.post("/api/schedule")
def daily_schedule(body: dict):
    """Turn the operating system's daily run on or off, at run_time from config.json."""
    at = json.loads(Path("config.json").read_text(encoding="utf-8")).get("run_time", "07:30")
    if body.get("on") and schedule.elsewhere():
        return {"ok": False, "scheduled": False, "why": "The daily task already starts another copy of the radar"}
    ok = schedule.install(at) if body.get("on") else schedule.remove()
    return {"ok": ok, "scheduled": schedule.status()}


@app.post("/api/setup/profile")
def setup_profile(body: dict):
    try:
        return {"ok": True, "chars": firstrun.save_profile(body.get("text"))}
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


@app.get("/api/doctor")
def doctor_report():
    """The same checks as python -m radar.doctor, for the setup page."""
    return {"checks": doctor.checks()}


@app.post("/api/run")
def run_radar(body: dict):
    return chat.run_radar(int(body.get("days", 1)), bool(body.get("all_tiers")))


@app.get("/api/run")
def run_status():
    return chat.run_status()


LOCAL_HOSTS = ("localhost", "127.0.0.1", "[::1]", "::1")


def allowed(method, origin):
    """Writes must come from this app's own page. A website open in another tab can send a request to localhost, and
    the browser labels it with that site's origin; those are refused. Requests with no origin (a terminal) pass."""
    if method in ("GET", "HEAD", "OPTIONS") or not origin:
        return True
    return urlparse(origin).hostname in LOCAL_HOSTS


@app.middleware("http")
async def same_origin_writes(request, call_next):
    if not allowed(request.method, request.headers.get("origin")):
        return JSONResponse({"detail": "requests from other websites are refused"}, status_code=403)
    return await call_next(request)


@app.middleware("http")
async def no_cache(request, call_next):
    """The page and its script change often; never let the browser keep a stale copy."""
    response = await call_next(request)
    if request.url.path.startswith("/web/"):
        response.headers["Cache-Control"] = "no-store"
    return response


app.mount("/web", StaticFiles(directory="web"), name="web")


@app.get("/")
def index():
    return RedirectResponse("/web/index.html")


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return RedirectResponse("/web/favicon.svg")


if __name__ == "__main__":
    UI_DIR.mkdir(parents=True, exist_ok=True)
    ready = lambda: not any(c["level"] == "fix" for c in doctor.checks())  # noqa: E731
    autorun.start(lambda: chat.run_radar(1, False), ready)  # the daily run while the app is open, with catch-up
    port = int(os.environ.get("RADAR_PORT", "8000"))  # another port when 8000 is taken
    threading.Timer(1.0, lambda: webbrowser.open(f"http://localhost:{port}")).start()
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")
