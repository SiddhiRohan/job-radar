"""Stop personal details from entering a commit.

Reads words to block from three private places that never enter git: the `.privacy-terms` file (one word or phrase
per line, # for comments), the owner settings in `.env` (OWNER_NAME, OWNER_SHORT, GMAIL_ADDRESS and the resume file
name), and the requisition ids in `applications.md`. With none of them present, as on a contributor's machine, it
passes. Matches are reported by file and line with the term's position in the list, never the term itself, so the
output is safe to paste anywhere.

    python scripts/privacy_guard.py FILE ...     pre-commit passes the staged files
    python scripts/privacy_guard.py --all        every tracked file
    python scripts/privacy_guard.py --text < t   a PR body or a commit message
"""

import re
import subprocess
import sys
from pathlib import Path

SKIP = (".png", ".jpg", ".jpeg", ".webp", ".gif", ".ico", ".mp4", ".docx", ".pdf", ".zip")
ENV_KEYS = ("OWNER_NAME", "OWNER_SHORT", "GMAIL_ADDRESS", "RESUME_FILENAME")


def env_values(path=Path(".env")):
    out = []
    if path.exists():
        for raw in path.read_text(encoding="utf-8").splitlines():
            key, _, value = raw.strip().partition("=")
            value = value.strip().strip('"').strip("'")
            if key in ENV_KEYS and value:
                out.append(value.rsplit(".", 1)[0] if key == "RESUME_FILENAME" else value)
    return out


def req_ids(path=Path("applications.md")):
    if not path.exists():
        return []
    ids = []
    for line in path.read_text(encoding="utf-8").splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) == 6 and len(cells[5]) >= 5 and cells[5] != "req_id":
            ids.append(cells[5])
    return ids


def terms(root=Path(".")):
    """Every blocked term, longest first so a full name is reported before its first name."""
    listed = []
    tf = root / ".privacy-terms"
    if tf.exists():
        listed = [t.strip() for t in tf.read_text(encoding="utf-8").splitlines() if t.strip() and not t.startswith("#")]
    found = listed + env_values(root / ".env") + req_ids(root / "applications.md")
    return sorted({t for t in found if len(t) >= 3}, key=len, reverse=True)


def pattern(term):
    return re.compile(rf"(?<![A-Za-z0-9]){re.escape(term)}(?![A-Za-z0-9])", re.I)


def scan_text(text, compiled):
    """(line number, term index) for every line holding a blocked term."""
    hits = []
    for n, line in enumerate(text.splitlines(), 1):
        for i, rx in compiled:
            if rx.search(line):
                hits.append((n, i))
                break
    return hits


def main(argv):
    blocked = terms()
    if not blocked:
        return 0
    compiled = [(i + 1, pattern(t)) for i, t in enumerate(blocked)]
    if argv[:1] == ["--text"]:
        hits = scan_text(sys.stdin.read(), compiled)
        for n, i in hits:
            print(f"text line {n}: personal term #{i}")
        return 1 if hits else 0
    files = (
        subprocess.run(["git", "ls-files"], capture_output=True, text=True).stdout.split()
        if argv[:1] == ["--all"]
        else argv
    )
    bad = 0
    for f in files:
        if f.lower().endswith(SKIP) or not Path(f).is_file():
            continue
        for n, i in scan_text(Path(f).read_text(encoding="utf-8", errors="ignore"), compiled):
            print(f"{f}:{n}: personal term #{i}")
            bad += 1
    if bad:
        print(f"{bad} line(s) hold personal details; edit them out (terms: .privacy-terms, .env, applications.md)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
