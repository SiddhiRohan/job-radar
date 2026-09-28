"""The setup page's work: save the resume, the API key and the profile the person enters in the browser.

Nothing here reads a secret back out: the key is written to .env and only ever reported as set or not set."""

import base64
from pathlib import Path

import requests

from radar import llm
from tailoring import resumes

KINDS = (".docx", ".txt", ".md")
MAX_BYTES = 5_000_000
PROFILE_MAX = 6000
COUNT_URL = "https://api.anthropic.com/v1/messages/count_tokens"


def state():
    """What the setup page shows: resume layout, whether a key and a profile exist, and the profile text."""
    paths = resumes.base_paths()
    names = sorted({p.name for p in paths.values()}) if paths else []
    profile = Path("profile.md").read_text(encoding="utf-8") if Path("profile.md").exists() else ""
    return {
        "resume": names,
        "original_layout": resumes.legacy(),
        "key_set": bool(read_env().get("ANTHROPIC_API_KEY")),
        "profile": profile,
    }


def save_resume(name, data_b64, root=None):
    """Write an uploaded resume to Resume/resume.<ext>. Refused for the original folder tree, which it would not use."""
    root = Path(root or resumes.ROOT)
    ext = Path(name or "").suffix.lower()
    if ext not in KINDS:
        raise ValueError("use a Word file (.docx); a .txt or .md resume works for scoring only")
    if resumes.legacy():
        raise ValueError("this folder uses the original Resume/ tree; change those files directly")
    data = base64.b64decode(data_b64, validate=True)
    if len(data) > MAX_BYTES:
        raise ValueError("that file is over 5 MB; a resume is usually under 200 KB")
    root.mkdir(parents=True, exist_ok=True)
    for old in root.glob("resume.*"):  # one resume file, so the layout stays unambiguous
        if old.suffix.lower() in KINDS:
            old.unlink()
    target = root / f"resume{ext}"
    target.write_bytes(data)
    return target.name


def read_env(path=Path(".env")):
    out = {}
    if path.exists():
        for raw in path.read_text(encoding="utf-8").splitlines():
            k, sep, v = raw.strip().partition("=")
            if sep and not k.startswith("#"):
                out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def write_env(key, value, path=Path(".env")):
    """Set one KEY=value line in .env, keeping every other line and comment as it was."""
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    for i, raw in enumerate(lines):
        if raw.strip().partition("=")[0].strip() == key:
            lines[i] = f"{key}={value}"
            break
    else:
        lines.append(f"{key}={value}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def check_key(key, post=requests.post):
    """Returns ok, rejected or unchecked (offline). Counting tokens is free, so checking costs nothing."""
    body = {"model": llm.MODELS[0], "messages": [{"role": "user", "content": "hello"}]}
    headers = {"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"}
    try:
        r = post(COUNT_URL, headers=headers, json=body, timeout=20)
    except requests.RequestException:
        return "unchecked"
    return "ok" if r.status_code == 200 else "rejected" if r.status_code in (401, 403) else "unchecked"


def save_key(key, post=requests.post):
    key = (key or "").strip()
    if not key.startswith("sk-ant-") or len(key) < 30 or any(c.isspace() for c in key):
        raise ValueError("that does not look like an Anthropic API key; it starts with sk-ant-")
    verdict = check_key(key, post)
    if verdict == "rejected":
        raise ValueError("Anthropic did not accept that key; copy it again from console.anthropic.com")
    write_env("ANTHROPIC_API_KEY", key)
    return verdict


def save_profile(text):
    text = (text or "").strip()
    if not text:
        raise ValueError("write a few lines first: roles, level, where you can work, sponsorship, pay floor")
    Path("profile.md").write_text(text[:PROFILE_MAX] + "\n", encoding="utf-8")
    return len(text)
