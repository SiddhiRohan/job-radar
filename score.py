"""Score new postings against the resume with Claude; write verdicts back into jobs.jsonl."""
import html
import json
import os
import re
import subprocess
import sys
import time
import zipfile
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
        "score": {"type": "integer", "enum": [1, 2, 3, 4, 5]},
        "hard_requirements_missing": {"type": "array", "items": {"type": "string"}},
        "why": {"type": "string", "description": "two sentences max"},
        "sponsorship_note": {"type": ["string", "null"]},
        "apply": {"type": "boolean"},
    },
    "required": ["score", "hard_requirements_missing", "why", "sponsorship_note", "apply"],
    "additionalProperties": False,
}


def find_resume():
    """resume.md / resume.pdf first, else any *resume*.{md,pdf,docx} in the folder."""
    for name in ("resume.md", "resume.pdf"):
        if Path(name).exists():
            return Path(name)
    hits = [p for p in Path(".").iterdir() if "resume" in p.name.lower() and p.suffix.lower() in (".md", ".pdf", ".docx")]
    return hits[0] if hits else sys.exit("no resume.md / resume.pdf / *resume*.docx in this folder")


def read_resume():
    path = find_resume()
    if path.suffix.lower() == ".md":
        return path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".docx":  # a docx is a zip; paragraphs are <w:p>, runs are <w:t>
        xml = zipfile.ZipFile(path).read("word/document.xml").decode("utf-8")
        xml = re.sub(r"<w:tab/>", " ", xml)
        paras = re.findall(r"<w:p[ >].*?</w:p>", xml, flags=re.S)
        return "\n".join(html.unescape("".join(re.findall(r"<w:t(?:\s[^>]*)?>(.*?)</w:t>", p, flags=re.S)))
                         for p in paras)
    try:
        return subprocess.run(["pdftotext", "-layout", str(path), "-"], capture_output=True,
                              text=True, encoding="utf-8", check=True).stdout
    except (FileNotFoundError, subprocess.CalledProcessError):
        from pypdf import PdfReader
        return "\n".join(p.extract_text() or "" for p in PdfReader(path).pages)


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
        if r.status_code != 200:
            raise RuntimeError(f"API {r.status_code}: {r.text[:300]}")
        data = r.json()
        if data.get("stop_reason") == "refusal":
            return {"error": "refusal"}, model
        text = "".join(b["text"] for b in data["content"] if b["type"] == "text")
        return json.loads(text), model
    sys.exit(f"none of {MODELS} worked for this API key")


def load_jobs():
    p = Path("jobs.jsonl")
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()] if p.exists() else []


def load_api_key():
    """ANTHROPIC_API_KEY from the environment, else from a KEY=VALUE line in .env."""
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key and Path(".env").exists():
        for raw in Path(".env").read_text(encoding="utf-8").splitlines():
            name, _, value = raw.strip().partition("=")
            if name == "ANTHROPIC_API_KEY":
                key = value.strip().strip('"').strip("'")
    return key or sys.exit("ANTHROPIC_API_KEY is not set (put it in .env as ANTHROPIC_API_KEY=sk-ant-...)")


def main():
    api_key = load_api_key()
    resume = read_resume()
    terms = json.load(open("config.json", encoding="utf-8"))["search_terms"]
    sites = {c["name"]: c for c in json.load(open("companies.json", encoding="utf-8"))}
    jobs = load_jobs()

    def unscored(j):  # never scored, or a previous attempt errored out
        return "verdict" not in j or "error" in (j["verdict"] or {})
    todo = [j for j in jobs if unscored(j)]
    todo.sort(key=lambda j: (terms.index(j["search_term"]) if j.get("search_term") in terms else 99,
                             j["posted_days_ago"]))
    todo = todo[:MAX_PER_RUN]
    print(f"scoring {len(todo)} of {sum(unscored(j) for j in jobs)} unscored postings")

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
