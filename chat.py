"""Chat assistant that drives the UI: tools for navigation, refresh, running the radar, applied tracking, tailoring edits.
Server-side tools run here; page tools are returned as actions for the browser to execute."""

import json
import subprocess
import sys
from pathlib import Path

import llm

SYSTEM = """You are the assistant inside a personal job-radar app. Rohan (F-1 OPT, needs H-1B, targets Data Engineer,
Data Scientist, ML Engineer, AI Engineer roles) is working through today's shortlist. Be brief and plain; sentence case;
no flattery. Use tools to act instead of describing what he could do. After acting, say in one line what you did.
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
        "description": "Poll the companies for new postings, score them, rebuild the digest, and pre-plan Apply rows. Takes 25-45 minutes; runs in the background. Use days>1 to widen the window when the shortlist is exhausted.",
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
        "description": "Record that Rohan applied to a posting.",
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
TOOLS.append(
    {
        "name": "remember",
        "description": "Save a durable fact or preference to memory.md so future chats know it (e.g. 'skip Booz Allen', 'prefers remote', 'applied to Adobe R171718 on 2026-09-14 via the Workday form'). One short sentence.",
        "input_schema": {"type": "object", "properties": {"note": {"type": "string"}}, "required": ["note"]},
    }
)
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
    RUN["log"].parent.mkdir(parents=True, exist_ok=True)
    args = [sys.executable, "run.py", "--days", str(days)] + (["--all-tiers"] if all_tiers else [])
    RUN["proc"] = subprocess.Popen(args, stdout=open(RUN["log"], "w", encoding="utf-8"), stderr=subprocess.STDOUT)
    return {
        "started": True,
        "days": days,
        "all_tiers": all_tiers,
        "note": "poll, score, digest, prepare; refresh Today when done",
    }


def run_status():
    p = RUN["proc"]
    last = (
        RUN["log"].read_text(encoding="utf-8", errors="replace").strip().splitlines()[-1:]
        if RUN["log"].exists()
        else []
    )
    return {
        "running": bool(p and p.poll() is None),
        "exit_code": p.poll() if p else None,
        "last_line": last[0][:160] if last else "",
    }


def server_tool(name, args, hooks):
    if name == "run_radar":
        return run_radar(args.get("days", 1), args.get("all_tiers", False))
    if name == "run_status":
        return run_status()
    if name == "mark_applied":
        return hooks["mark_applied"](args)
    if name == "set_status":
        return hooks["set_status"](args)
    if name == "remember":
        return remember(args.get("note", ""))
    return {"error": f"unknown tool {name}"}


def message(session_id, text, context, hooks, max_turns=6):
    """One user message -> (reply text, page actions). Server tools execute here; page tools are queued for the browser."""
    history = load_session(session_id)
    history.append({"role": "user", "content": text})
    memory = MEMORY.read_text(encoding="utf-8") if MEMORY.exists() else "(empty)"
    applied = hooks["applied_rows"]()
    system = (
        SYSTEM
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
