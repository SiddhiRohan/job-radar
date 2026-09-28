"""Score new postings against both resume bases with Claude; write verdicts back into jobs.jsonl.
The prompt and the verdict schema, fit factors included, live in radar/fit.py."""

import json
import os
import sys
import time
from pathlib import Path

import requests

from radar import batch, filters, fit, llm, store
from tailoring import resumes

sys.stdout.reconfigure(encoding="utf-8")

API_URL = "https://api.anthropic.com/v1/messages"
MODELS = llm.MODELS  # one place picks the model: ANTHROPIC_MODEL in the environment or .env
MAX_DESC_CHARS = 12000


NO_KEY = (
    "ANTHROPIC_API_KEY is not set: put it in .env as ANTHROPIC_API_KEY=sk-ant-..., "
    "or score in a coding assistant with /radar-score (python -m radar.handscore)"
)


def load_api_key(required=True):
    """ANTHROPIC_API_KEY from the environment, else from a KEY=VALUE line in .env. Without one: exit, or None when
    the caller can do without."""
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key and Path(".env").exists():
        for raw in Path(".env").read_text(encoding="utf-8").splitlines():
            name, _, value = raw.strip().partition("=")
            if name == "ANTHROPIC_API_KEY":
                key = value.strip().strip('"').strip("'")
    if key or not required:
        return key or None
    sys.exit(NO_KEY)


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


def body(model, system, job):
    """The Messages API request for one posting; a direct call and a batch send the same one."""
    user = (
        f"JOB POSTING: {job['title']} at {job['company']} ({job['location']})\n"
        f"Regex sponsorship read: {job.get('sponsorship')} ({job.get('sponsorship_evidence') or 'no phrase found'})\n\n"
        f"{job.get('description', '')[:MAX_DESC_CHARS]}\n\nReturn the JSON verdict."
    )
    return {
        "model": model,
        "max_tokens": 1536,
        "system": system,
        "messages": [{"role": "user", "content": user}],
        "output_config": {"format": {"type": "json_schema", "schema": fit.SCHEMA}},
    }


def ask_claude(api_key, system, job):
    """Return (verdict dict, model used). Falls back through MODELS on not_found."""
    headers = {"x-api-key": api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"}
    for model in MODELS:
        for attempt in range(3):
            r = requests.post(API_URL, headers=headers, json=body(model, system, job), timeout=120)
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


def settle(j, verdict):
    j["verdict"] = verdict
    s = f"E{verdict.get('score_entry', '-')}/X{verdict.get('score_experienced', '-')}"
    why = (verdict.get("why") or verdict.get("error", ""))[:70]
    print(f"  [{s}] {j['company']:<12} {j['title'][:55]:<55} {why}", flush=True)


def early(j):
    """Entry-level titles and postings asking two years or fewer go first, so the cap never starves them."""
    years = j.get("years_required")
    return filters.is_entry_title(j["title"]) or (years is not None and years <= 2)


def queue(jobs):
    """Unscored postings in the order they are scored: early ones first, then the newest. A run and a coding
    assistant (radar/handscore.py) take them in this order."""
    return sorted((j for j in jobs if unscored(j)), key=lambda j: (0 if early(j) else 1, j["posted_days_ago"]))


def main():
    cfg = json.load(open("config.json", encoding="utf-8"))
    cap = cfg.get("score_cap", 40)
    jobs = store.load()
    todo, ask = queue(jobs), []
    for j in todo:  # a hard rule settles a posting with no model, so with no key as well
        verdict = rule_verdict(j)
        if verdict:
            settle(j, verdict)
        elif len(ask) < cap:
            ask.append(j)
    api_key = load_api_key(required=False) if ask else None
    print(f"{len(todo)} unscored postings, {len(ask)} for the model (cap {cap}); API key set: {bool(api_key)}")
    if ask and not api_key:
        print(NO_KEY, flush=True)
        ask = []
    system = system_blocks() if ask else None
    batched = cfg.get("score_batch") and ask and batch.score(api_key, [body(MODELS[0], system, j) for j in ask])
    for i, j in enumerate(ask):
        if batched and i in batched:
            verdict, j["scored_with"] = batched[i]
        else:
            try:
                verdict, j["scored_with"] = ask_claude(api_key, system, j)
            except Exception as e:  # record the failure on the posting; retried next run
                verdict = {"error": str(e)[:300]}
        settle(j, verdict)
    store.save(jobs)  # keeps rows added while scoring ran, such as a link pasted during a batch's wait
    print(f"done: {len(ask)} postings sent to the model, {len(batched or {})} of them in a batch")


if __name__ == "__main__":
    main()
