"""Score new postings against both resume bases with Claude; write verdicts back into jobs.jsonl.
The prompt and the verdict schema, fit factors included, live in radar/fit.py."""

import json
import os
import sys
import time
from pathlib import Path

import requests

from radar import filters, fit, store
from tailoring import resumes

sys.stdout.reconfigure(encoding="utf-8")

API_URL = "https://api.anthropic.com/v1/messages"
MODELS = [os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6"), "claude-sonnet-5", "claude-opus-5"]
MAX_DESC_CHARS = 12000


def load_api_key():
    """ANTHROPIC_API_KEY from the environment, else from a KEY=VALUE line in .env."""
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key and Path(".env").exists():
        for raw in Path(".env").read_text(encoding="utf-8").splitlines():
            name, _, value = raw.strip().partition("=")
            if name == "ANTHROPIC_API_KEY":
                key = value.strip().strip('"').strip("'")
    return key or sys.exit("ANTHROPIC_API_KEY is not set (put it in .env as ANTHROPIC_API_KEY=sk-ant-...)")


def system_blocks():
    """Stable prefix (rules, profile, both resumes) with a cache breakpoint so 100+ calls reuse it."""
    profile = resumes.profile_text()
    roles = ", ".join(
        f"{r} ({', '.join(v for v, ok in s.items() if ok) or 'EMPTY'})" for r, s in resumes.role_status().items()
    )
    b = resumes.bases()
    return [
        {"type": "text", "text": f"{fit.RULES}\n\nCANDIDATE PROFILE:\n{profile}\nROLE FOLDERS AVAILABLE: {roles}"},
        {"type": "text", "text": "ENTRY-LEVEL BASE RESUME (framed as about 2 years):\n" + b["entry"]},
        {
            "type": "text",
            "text": "EXPERIENCED BASE RESUME (about 4 years):\n" + b["experienced"],
            "cache_control": {"type": "ephemeral"},
        },
    ]


def ask_claude(api_key, system, job):
    """Return (verdict dict, model used). Falls back through MODELS on not_found."""
    user = (
        f"JOB POSTING: {job['title']} at {job['company']} ({job['location']})\n"
        f"Regex sponsorship read: {job.get('sponsorship')} ({job.get('sponsorship_evidence') or 'no phrase found'})\n\n"
        f"{job.get('description', '')[:MAX_DESC_CHARS]}\n\nReturn the JSON verdict."
    )
    headers = {"x-api-key": api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"}
    for model in MODELS:
        body = {
            "model": model,
            "max_tokens": 1536,
            "system": system,
            "messages": [{"role": "user", "content": user}],
            "output_config": {"format": {"type": "json_schema", "schema": fit.SCHEMA}},
        }
        for attempt in range(3):
            r = requests.post(API_URL, headers=headers, json=body, timeout=120)
            if r.status_code in (429, 529) or r.status_code >= 500:
                time.sleep(5 * (attempt + 1))
                continue
            break
        if r.status_code == 404 and "not_found" in r.text:
            print(f"  model {model} not available, trying next", flush=True)
            continue
        if r.status_code != 200:
            raise RuntimeError(f"API {r.status_code}: {r.text[:300]}")
        data = r.json()
        if data.get("stop_reason") == "refusal":
            return {"error": "refusal"}, model
        return json.loads("".join(b["text"] for b in data["content"] if b["type"] == "text")), model
    sys.exit(f"none of {MODELS} worked for this API key")


def rule_verdict(j):
    """Skip the API when a hard rule already decides: years gate, sponsorship no, PERM ad. Its factors list is empty:
    no model read the posting, so there is no experience, level, skills or domain judgment to show; the drawer
    still shows sponsorship, location and pay (radar/factors.py), and why names the rule."""
    if j.get("years_gate"):
        why = f"years gate: {j['years_required']}+ years required"
    elif j.get("sponsorship") in ("no", "perm_ad"):
        why = f"skipped: sponsorship {j['sponsorship']}"
    else:
        return None
    return {
        "factors": [],
        "score_entry": 1,
        "score_experienced": 1,
        "recommended_resume": None,
        "recommended_variant": None,
        "years_required": j.get("years_required"),
        "hard_requirements_missing": [],
        "platform_tools_missing": [],
        "sponsorship": j.get("sponsorship"),
        "sponsorship_evidence": j.get("sponsorship_evidence"),
        "cover_letter_required": False,
        "why": why,
        "apply": False,
        "rule": True,
    }


def unscored(j):
    return "score_entry" not in (j.get("verdict") or {})


def main():
    api_key = load_api_key()
    print("ANTHROPIC_API_KEY set:", bool(api_key))
    cfg = json.load(open("config.json", encoding="utf-8"))
    cap = cfg.get("score_cap", 40)
    jobs = store.load()
    # Entry-level and low-years postings first, so the cap never starves them; then newest.
    todo = sorted(
        (j for j in jobs if unscored(j)),
        key=lambda j: (
            0
            if filters.is_entry_title(j["title"]) or (j.get("years_required") is not None and j["years_required"] <= 2)
            else 1,
            j["posted_days_ago"],
        ),
    )
    print(f"{len(todo)} unscored postings; API cap {cap}")
    system, calls = system_blocks(), 0
    for j in todo:
        verdict = rule_verdict(j)
        if verdict is None:
            if calls >= cap:
                continue
            calls += 1
            try:
                verdict, j["scored_with"] = ask_claude(api_key, system, j)
            except Exception as e:  # record the failure on the posting; retried next run
                verdict = {"error": str(e)[:300]}
        j["verdict"] = verdict
        s = f"E{verdict.get('score_entry', '-')}/X{verdict.get('score_experienced', '-')}"
        print(
            f"  [{s}] {j['company']:<12} {j['title'][:55]:<55} {(verdict.get('why') or verdict.get('error', ''))[:70]}",
            flush=True,
        )
    with open("jobs.jsonl", "w", encoding="utf-8") as f:
        for j in jobs:
            f.write(json.dumps(j) + "\n")
    print(f"done: {calls} API calls")


if __name__ == "__main__":
    main()
