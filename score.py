"""Score new postings against the resume with Claude; write verdicts back into jobs.jsonl."""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import requests

import wd

sys.stdout.reconfigure(encoding="utf-8")

API_URL = "https://api.anthropic.com/v1/messages"
MODELS = [os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6"), "claude-sonnet-5", "claude-opus-5"]
MAX_PER_RUN = 40
MAX_DESC_CHARS = 12000

SYSTEM = """You are a blunt technical recruiter screening a candidate against a job posting.
Score 5 = candidate clearly meets every must-have. 4 = meets must-haves, minor gaps.
3 = plausible with a tailored resume. 2 = significant gaps. 1 = don't bother.
No flattery. Quote sponsorship/visa/citizenship/clearance language verbatim if present."""

SCHEMA = {
    "type": "object",
    "properties": {
        "score": {"type": "integer", "minimum": 1, "maximum": 5},
        "hard_requirements_missing": {"type": "array", "items": {"type": "string"}},
        "why": {"type": "string", "description": "two sentences max"},
        "sponsorship_note": {"type": ["string", "null"]},
        "apply": {"type": "boolean"},
    },
    "required": ["score", "hard_requirements_missing", "why", "sponsorship_note", "apply"],
    "additionalProperties": False,
}


def read_resume():
    if Path("resume.md").exists():
        return Path("resume.md").read_text(encoding="utf-8")
    if Path("resume.pdf").exists():
        try:
            return subprocess.run(["pdftotext", "-layout", "resume.pdf", "-"], capture_output=True,
                                  text=True, encoding="utf-8", check=True).stdout
        except (FileNotFoundError, subprocess.CalledProcessError):
            from pypdf import PdfReader
            return "\n".join(p.extract_text() or "" for p in PdfReader("resume.pdf").pages)
    sys.exit("no resume.md or resume.pdf in this folder")


def ask_claude(api_key, resume, job, description):
    """Return (verdict dict, model used). Falls back through MODELS on not_found."""
    user = (f"RESUME:\n{resume}\n\nJOB POSTING: {job['title']} at {job['company']} ({job['location']})\n"
            f"{description[:MAX_DESC_CHARS]}\n\nReturn the JSON verdict.")
    headers = {"x-api-key": api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"}
    for model in MODELS:
        body = {"model": model, "max_tokens": 1024, "system": SYSTEM,
                "messages": [{"role": "user", "content": user}],
                "output_config": {"format": {"type": "json_schema", "schema": SCHEMA}}}
        for attempt in range(3):
            r = requests.post(API_URL, headers=headers, json=body, timeout=120)
            if r.status_code in (429, 529) or r.status_code >= 500:
                time.sleep(5 * (attempt + 1))
                continue
            break
        if r.status_code == 404 and "not_found" in r.text:
            print(f"  model {model} not available, trying next", flush=True)
            continue
        r.raise_for_status()
        data = r.json()
        if data.get("stop_reason") == "refusal":
            return {"error": "refusal"}, model
        text = "".join(b["text"] for b in data["content"] if b["type"] == "text")
        return json.loads(text), model
    sys.exit(f"none of {MODELS} worked for this API key")


def load_jobs():
    p = Path("jobs.jsonl")
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()] if p.exists() else []


def main():
    api_key = os.environ.get("ANTHROPIC_API_KEY") or sys.exit("ANTHROPIC_API_KEY is not set")
    resume = read_resume()
    terms = json.load(open("config.json", encoding="utf-8"))["search_terms"]
    sites = {c["name"]: c for c in json.load(open("companies.json", encoding="utf-8"))}
    jobs = load_jobs()

    todo = [j for j in jobs if "verdict" not in j]
    todo.sort(key=lambda j: (terms.index(j["search_term"]) if j.get("search_term") in terms else 99,
                             j["posted_days_ago"]))
    todo = todo[:MAX_PER_RUN]
    print(f"scoring {len(todo)} of {sum('verdict' not in j for j in jobs)} unscored postings")

    for j in todo:
        c = sites[j["company"]]
        try:
            desc = wd.fetch_description(c["tenant"], c["shard"], j["detail_path"])
            verdict, model = ask_claude(api_key, resume, j, desc)
        except Exception as e:  # keep going; record the failure on the posting
            verdict, model = {"error": str(e)[:200]}, None
        j["verdict"] = verdict
        j["scored_with"] = model
        s = verdict.get("score", "-")
        print(f"  [{s}] {j['company']:<12} {j['title'][:60]:<60} {verdict.get('why', verdict.get('error', ''))[:80]}",
              flush=True)

    with open("jobs.jsonl", "w", encoding="utf-8") as f:
        for j in jobs:
            f.write(json.dumps(j) + "\n")


if __name__ == "__main__":
    main()
