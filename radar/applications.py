"""applications.md: the table of postings the owner applied to. Read and written by the web app and the mail step."""

from pathlib import Path

PATH = Path("applications.md")
CAP = ["date", "company", "title", "status", "folder", "req_id"]
STATUSES = ("applied", "screen", "interview", "rejected", "offer")
# Forward-only order for automatic updates: a late confirmation email must never undo "interview".
RANK = {"applied": 0, "screen": 1, "interview": 2, "rejected": 3, "offer": 4}


def rows(path=None):
    p = Path(path or PATH)
    if not p.exists():
        return []
    out = []
    for line in p.read_text(encoding="utf-8").splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) == 6 and cells[0] not in ("date", "---") and not set(cells[0]) <= {"-"}:
            out.append(dict(zip(CAP, cells)))
    return out


def write(items, path=None):
    lines = ["| date | company | title | status | folder | req_id |", "|---|---|---|---|---|---|"]
    lines += ["| " + " | ".join(str(r.get(c, "")).replace("|", "/") for c in CAP) + " |" for r in items]
    Path(path or PATH).write_text("\n".join(lines) + "\n", encoding="utf-8")


def set_status(company, req_id, status, forward_only=False, path=None):
    """Change one application's status. Returns (old, new), or None if no such application or the change is refused."""
    if status not in STATUSES:
        return None
    items = rows(path)
    for r in items:
        if r["company"] == company and r["req_id"] == req_id:
            old = r["status"]
            if forward_only and RANK.get(status, -1) <= RANK.get(old, -1):
                return None
            r["status"] = status
            write(items, path)
            return old, status
    return None
