"""Chat assistant that drives the UI: tools for navigation, refresh, running the radar, applied tracking, tailoring edits.
Server-side tools run here; page tools are returned as actions for the browser to execute."""

import json
import subprocess
import sys
from pathlib import Path

from radar import agentchat, llm, owner, runlock

SYSTEM = """You are the assistant inside a personal job-radar app. {name} is working through today's shortlist; the
PROFILE section below says who they are and what they target. Be brief and plain; sentence case;
no flattery. Use tools to act instead of describing what they could do. After acting, say in one line what you did.
Finding postings comes first; tailoring a resume is on demand: tailor_posting to plan, then build_resume for the
docx and its download link, then save_resume. Summarise a plan as the fit line plus the changed bullets, not the
whole resume. open_tailor only when they ask to see or edit the full side-by-side.
When they ask about replies, rejections or interviews, use check_mail, say what moved and what needs review, then
navigate to applied so they can settle the review items. When they ask whether a posting is still up, or why an
application is quiet, use posting_status: a closed posting with no reply is usually the answer. For "what should I
do today" or "what changed", use morning_brief and lead with its picks. When they paste a job link or ask whether a
job suits them, use evaluate_link and explain the verdict plainly, gaps included. To follow a new employer, use
add_employer with a link to its jobs; ask for the link if they did not give one. For an interview, use
interview_prep and lead with the questions and the stories; for quiet applications, follow_ups; for what to learn,
skill_gaps; for which employers sponsor, sponsor_map. When they tell you how an interview went, pass their account to
interview_debrief in their own words, lead with the weak answers and the thank-you note, set the application's status
if it is behind, and offer a practice round: one weak question at a time, with feedback from the resume. For "am I
missing jobs" or "are my filters too strict", use filter_audit; change config.json only when they ask.
CONTEXT (what the page shows now) follows; the Today rows are ranked by score, E = entry base, X = experienced base."""

PAGE_TOOLS = {"navigate", "refresh", "open_tailor", "edit_section", "rebuild"}
TOOLS = [
    {
        "name": "navigate",
        "description": "Switch the page to a view.",
        "input_schema": {
            "type": "object",
            "properties": {"view": {"type": "string", "enum": ["today", "tailor", "applied"]}},
            "required": ["view"],
        },
    },
    {
        "name": "refresh",
        "description": "Reload the current view's data (after a run, or to drop applied rows into their done state).",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "run_radar",
        "description": "Poll the companies for new postings, score them, rebuild the digest, and read new hiring emails. Takes 25-45 minutes; runs in the background. Use days>1 to widen the window when the shortlist is exhausted.",
        "input_schema": {
            "type": "object",
            "properties": {"days": {"type": "integer", "minimum": 1, "maximum": 7}, "all_tiers": {"type": "boolean"}},
            "required": ["days"],
        },
    },
    {
        "name": "run_status",
        "description": "Whether a radar run is in progress and its last log line.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "mark_applied",
        "description": "Record that the owner applied to a posting.",
        "input_schema": {
            "type": "object",
            "properties": {"company": {"type": "string"}, "req_id": {"type": "string"}, "title": {"type": "string"}},
            "required": ["company", "req_id", "title"],
        },
    },
    {
        "name": "set_status",
        "description": "Change an application's status.",
        "input_schema": {
            "type": "object",
            "properties": {
                "company": {"type": "string"},
                "req_id": {"type": "string"},
                "status": {"type": "string", "enum": ["applied", "screen", "interview", "rejected", "offer"]},
            },
            "required": ["company", "req_id", "status"],
        },
    },
    {
        "name": "open_tailor",
        "description": "Open a posting in the Tailor view (by company and req_id, or a Workday URL).",
        "input_schema": {
            "type": "object",
            "properties": {"company": {"type": "string"}, "req_id": {"type": "string"}, "url": {"type": "string"}},
        },
    },
    {
        "name": "edit_section",
        "description": "Replace the tailored text of one item on the open Tailor view. section is the section id from context (summary, job0.., skills, coursework); index is the item within it. Keep ** bold markers; never change numbers, dates, titles, employers.",
        "input_schema": {
            "type": "object",
            "properties": {"section": {"type": "string"}, "index": {"type": "integer"}, "text": {"type": "string"}},
            "required": ["section", "index", "text"],
        },
    },
    {
        "name": "rebuild",
        "description": "Rebuild the resume docx from the current tailored text on the Tailor view.",
        "input_schema": {"type": "object", "properties": {}},
    },
]
TOOLS += [
    {
        "name": "tailor_posting",
        "description": "Plan a tailored resume for one posting (cached after the first time, about a minute otherwise). Returns the fit assessment, the changed sections with before/after text, JD skills outside the confirmed list, and notes. Use this when the user asks to tailor, adapt, or modify a resume for a posting.",
        "input_schema": {
            "type": "object",
            "properties": {
                "company": {"type": "string"},
                "req_id": {"type": "string"},
                "fresh": {"type": "boolean", "description": "true to ignore the cached plan"},
            },
            "required": ["company", "req_id"],
        },
    },
    {
        "name": "build_resume",
        "description": 'Build the .docx from the current plan for a posting (after tailor_posting), run finalize, and return the download URL. Pass edits to override section text first: {section_id: {"text": [..]}}.',
        "input_schema": {
            "type": "object",
            "properties": {"company": {"type": "string"}, "req_id": {"type": "string"}, "edits": {"type": "object"}},
            "required": ["company", "req_id"],
        },
    },
    {
        "name": "save_resume",
        "description": "Copy the last built files for a posting into Resume/For <Company>/<req>_<title>/ (or dest) with jd.txt and notes.md.",
        "input_schema": {
            "type": "object",
            "properties": {"company": {"type": "string"}, "req_id": {"type": "string"}, "dest": {"type": "string"}},
            "required": ["company", "req_id"],
        },
    },
]
TOOLS.append(
    {
        "name": "remember",
        "description": "Save a durable fact or preference to memory.md so future chats know it (e.g. 'skip Booz Allen', 'prefers remote', 'applied to Contoso R-12345 on 2026-09-14 via the Workday form'). One short sentence.",
        "input_schema": {"type": "object", "properties": {"note": {"type": "string"}}, "required": ["note"]},
    }
)
TOOLS.append(
    {
        "name": "morning_brief",
        "description": "The morning brief: the postings to apply to first with one line on why, status changes from email, postings that closed, applications that went quiet, and one pattern in the rejections. Use it for 'what should I do today' or 'what changed'.",
        "input_schema": {"type": "object", "properties": {}},
    }
)
TOOLS.append(
    {
        "name": "posting_status",
        "description": "Which open applications' postings have closed, been retitled, repriced or rewritten since applying, from the daily watch. A closed posting with no reply is the quiet rejection nobody emails about.",
        "input_schema": {"type": "object", "properties": {}},
    }
)
TOOLS.append(
    {
        "name": "rejection_patterns",
        "description": "Where the rejections cluster: rejection rate by title family, seniority wording, resume base, fit score, years asked, sponsorship default and company, compared with the overall rate. Counts only; says when there is too little data.",
        "input_schema": {"type": "object", "properties": {}},
    }
)
TOOLS.append(
    {
        "name": "check_mail",
        "description": "Read new hiring emails now (Gmail, read-only). An email carrying one application's req id and clear wording moves that status forward; other replies that could change a status go to the needs-review list on the Applied view. Returns how many moved, what needs review, or that Gmail is not set up. Takes a minute or two.",
        "input_schema": {"type": "object", "properties": {}},
    }
)
TOOLS += [
    {
        "name": "evaluate_link",
        "description": "Judge one posting from its link (Workday, Greenhouse, Lever or Ashby): fetches it once, scores it against the resume, stores it, and returns the fit per base, sponsorship, years asked, pay, gaps and why. A posting already stored comes back without a new request.",
        "input_schema": {"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]},
    },
    {
        "name": "add_employer",
        "description": "Add an employer to the daily search from a link to its jobs: its Workday careers site or any posting on it, or its Greenhouse, Lever or Ashby board. Checks the link with one request and says how many postings are open; the next run includes it.",
        "input_schema": {
            "type": "object",
            "properties": {"name": {"type": "string"}, "url": {"type": "string"}},
            "required": ["name", "url"],
        },
    },
]
TOOLS += agentchat.TOOLS
RUN = {"proc": None, "log": Path(".cache/ui/run.log")}
SESSIONS = {}
CHAT_DIR = Path(".cache/ui/chat")
MEMORY = Path("memory.md")


def load_session(session_id):
    if session_id not in SESSIONS:
        p = CHAT_DIR / f"{session_id}.json"
        SESSIONS[session_id] = json.loads(p.read_text(encoding="utf-8")) if p.exists() else []
    return SESSIONS[session_id]


def save_session(session_id):
    CHAT_DIR.mkdir(parents=True, exist_ok=True)
    (CHAT_DIR / f"{session_id}.json").write_text(json.dumps(SESSIONS[session_id]), encoding="utf-8")


def transcript(session_id):
    """Plain turns for the page: user text and assistant text only, tool traffic hidden."""
    out = []
    for m in load_session(session_id):
        if m["role"] == "user" and isinstance(m["content"], str):
            out.append({"who": "me", "text": m["content"]})
        elif m["role"] == "assistant":
            t = "".join(b.get("text", "") for b in m["content"] if b.get("type") == "text").strip()
            if t:
                out.append({"who": "bot", "text": t})
    return out


def sessions():
    """Saved threads, newest first: id, title (first user message), updated time."""
    out = []
    for p in CHAT_DIR.glob("*.json") if CHAT_DIR.exists() else []:
        turns = json.loads(p.read_text(encoding="utf-8"))
        first = next((m["content"] for m in turns if m["role"] == "user" and isinstance(m["content"], str)), "")
        out.append({"id": p.stem, "title": first[:60] or "Untitled", "updated": p.stat().st_mtime})
    return sorted(out, key=lambda s: -s["updated"])


def remember(note):
    from datetime import date

    MEMORY.touch()
    with MEMORY.open("a", encoding="utf-8") as f:
        f.write(f"- {date.today().isoformat()}: {note.strip()}\n")
    return {"saved": note.strip()}


def run_radar(days, all_tiers=False):
    if RUN["proc"] and RUN["proc"].poll() is None:
        return {"started": False, "reason": "a run is already in progress"}
    if runlock.held():  # started by the OS scheduler or a terminal, not by this app
        return {"started": False, "reason": f"a run started at {runlock.since()} is still going"}
    RUN["log"].parent.mkdir(parents=True, exist_ok=True)
    args = [sys.executable, "run.py", "--days", str(days)] + (["--all-tiers"] if all_tiers else [])
    RUN["proc"] = subprocess.Popen(args, stdout=open(RUN["log"], "w", encoding="utf-8"), stderr=subprocess.STDOUT)
    return {
        "started": True,
        "days": days,
        "all_tiers": all_tiers,
        "note": "poll, score, digest, mail; refresh Today when done",
    }


def run_status():
    p = RUN["proc"]
    last = (
        RUN["log"].read_text(encoding="utf-8", errors="replace").strip().splitlines()[-1:]
        if RUN["log"].exists()
        else []
    )
    own = bool(p and p.poll() is None)
    outside = not own and runlock.held()
    return {
        "running": own or outside,
        "exit_code": p.poll() if p else None,
        "last_line": f"a scheduled run started at {runlock.since()} is still going"
        if outside
        else (last[0][:160] if last else ""),
    }


def evaluate_link(url):
    """The verdict on one posting as the plain lines `python -m radar.evaluate` prints, or what went wrong."""
    from radar import evaluate

    try:
        return {"posting": evaluate.summary(evaluate.ingest_url(url))}
    except Exception as e:  # a bad link, a closed posting or a failed call: the model tells them in words
        return {"error": str(e)[:300]}


def server_tool(name, args, hooks):
    if name == "run_radar":
        return run_radar(args.get("days", 1), args.get("all_tiers", False))
    if name == "run_status":
        return run_status()
    if name == "evaluate_link":
        return evaluate_link(args.get("url", ""))
    if name == "add_employer":
        from companies import add  # reads the sponsorship lists from the repo root on import

        return add.add(args.get("name", ""), args.get("url", ""))
    if name == "mark_applied":
        return hooks["mark_applied"](args)
    if name == "set_status":
        return hooks["set_status"](args)
    if name == "remember":
        return remember(args.get("note", ""))
    if name in agentchat.NAMES:
        return agentchat.call(name, args)
    if name in (
        "tailor_posting",
        "build_resume",
        "save_resume",
        "check_mail",
        "rejection_patterns",
        "posting_status",
        "morning_brief",
    ):
        return hooks[name](args)
    return {"error": f"unknown tool {name}"}


def message(session_id, text, context, hooks, max_turns=6):
    """One user message -> (reply text, page actions). Server tools execute here; page tools are queued for the browser."""
    history = load_session(session_id)
    history.append({"role": "user", "content": text})
    memory = MEMORY.read_text(encoding="utf-8") if MEMORY.exists() else "(empty)"
    applied = hooks["applied_rows"]()
    profile = Path("profile.md").read_text(encoding="utf-8") if Path("profile.md").exists() else "(no profile.md yet)"
    system = (
        SYSTEM.replace("{name}", owner.short_name())
        + "\n\nPROFILE (profile.md):\n"
        + profile[:3000]
        + "\n\nMEMORY (memory.md, durable notes; add with the remember tool):\n"
        + memory[-4000:]
        + "\n\nAPPLICATIONS (applications.md):\n"
        + json.dumps(applied)[:4000]
        + "\n\n"
        + json.dumps(context)[:12000]
    )
    actions = []
    for _ in range(max_turns):
        resp = llm.converse(system, history, TOOLS)
        history.append({"role": "assistant", "content": resp["content"]})
        uses = [b for b in resp["content"] if b["type"] == "tool_use"]
        if resp.get("stop_reason") != "tool_use" or not uses:
            break
        results = []
        for u in uses:
            if u["name"] in PAGE_TOOLS:
                actions.append({"tool": u["name"], "args": u["input"]})
                out = {"queued": True, "note": "the page will execute this after your reply"}
            else:
                out = server_tool(u["name"], u["input"], hooks)
            results.append({"type": "tool_result", "tool_use_id": u["id"], "content": json.dumps(out)})
        history.append({"role": "user", "content": results})
    reply = (
        "".join(b.get("text", "") for b in history[-1]["content"] if isinstance(b, dict) and b.get("type") == "text")
        if history[-1]["role"] == "assistant"
        else ""
    )
    del history[:-40]  # keep the last 40 turns; memory.md and the page context carry the rest
    save_session(session_id)
    return {"reply": reply.strip(), "actions": actions}
