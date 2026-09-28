"""python -m radar.doctor [--brief]: check that everything the radar needs is in place, and say how to fix what is not.

Each check is ok, info or fix. "fix" means the radar cannot do its main job until it is fixed; exit code 1.
--brief prints only what needs attention, for the start script. The web app shows the same list."""

import importlib.util
import json
import socket
import sys
from datetime import datetime
from pathlib import Path

PACKAGES = {"requests": "requests", "docx": "python-docx", "fastapi": "fastapi", "uvicorn": "uvicorn"}


def env(key):
    if not Path(".env").exists():
        return ""
    for raw in Path(".env").read_text(encoding="utf-8").splitlines():
        k, _, v = raw.strip().partition("=")
        if k == key:
            return v.strip().strip('"').strip("'")
    return ""


def item(level, what, detail=""):
    return {"level": level, "what": what, "detail": detail}


def checks():
    out = []
    v = sys.version_info
    out.append(
        item("ok", f"Python {v.major}.{v.minor}")
        if v >= (3, 11)
        else item("fix", f"Python {v.major}.{v.minor} is too old", "install 3.11 or newer from python.org")
    )
    missing = [pip for mod, pip in PACKAGES.items() if importlib.util.find_spec(mod) is None]
    out.append(
        item("fix", "Packages missing: " + ", ".join(missing), "run start again, or: pip install -r requirements.txt")
        if missing
        else item("ok", "Packages installed")
    )
    try:
        from tailoring import resumes

        paths = resumes.base_paths()
    except Exception as e:  # a broken resume file must not hide the other checks
        paths, err = {}, str(e)[:80]
    else:
        err = ""
    if paths:
        kind = "one resume" if paths["entry"] == paths["experienced"] else "entry and experienced resumes"
        out.append(item("ok", f"Resume: {kind}", ", ".join(sorted({p.name for p in paths.values()}))))
    else:
        out.append(item("fix", "No resume found", err or "put yours in Resume/ as resume.docx"))
    out.append(
        item("ok", "Profile: profile.md")
        if Path("profile.md").exists()
        else item("info", "No profile.md", "optional: a few lines on target roles make scores sharper")
    )
    out.append(
        item("ok", "Anthropic API key set")
        if env("ANTHROPIC_API_KEY")
        else item("fix", "No Anthropic API key", "add ANTHROPIC_API_KEY=... to .env; keys: console.anthropic.com")
    )
    for name in ("config.json", "companies.json"):
        try:
            data = json.loads(Path(name).read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:
            out.append(item("fix", f"{name} unreadable", str(e)[:80]))
            continue
        if name == "companies.json":
            out.append(item("ok", f"{sum(1 for c in data if c.get('verified'))} employers to poll"))
    out.append(
        item("ok", "Email statuses on")
        if env("GMAIL_ADDRESS") and env("GMAIL_APP_PASSWORD")
        else item("info", "Email statuses off", "optional: see Email in docs/CONFIG.md")
    )
    out.append(last_run())
    return out


def last_run(path=Path("last_run.json")):
    try:
        ran = datetime.fromisoformat(json.loads(path.read_text(encoding="utf-8"))["ran_at"]).astimezone()
    except (OSError, ValueError, KeyError):
        return item("info", "No run yet", "the app runs one at run_time, or press Run the radar")
    hours = (datetime.now().astimezone() - ran).total_seconds() / 3600
    return item(
        "ok" if hours < 30 else "info", f"Last run {ran:%Y-%m-%d %H:%M}", "" if hours < 30 else "over a day ago"
    )


def app_running(port=8000):
    with socket.socket() as s:
        s.settimeout(0.3)
        return s.connect_ex(("127.0.0.1", port)) == 0


def main(argv):
    brief = "--brief" in argv
    marks = {"ok": "ok  ", "info": "note", "fix": "FIX "}
    found = checks()
    for c in found:
        if brief and c["level"] == "ok":
            continue
        print(f"  {marks[c['level']]} {c['what']}" + (f": {c['detail']}" if c["detail"] else ""))
    fixes = sum(c["level"] == "fix" for c in found)
    print(f"doctor: {fixes} to fix" if fixes else "doctor: ready")
    return 1 if fixes else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main(sys.argv[1:]))
