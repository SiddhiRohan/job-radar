"""applications.md: the table of postings the owner applied to. Read and written by the web app and the mail step.

python -m radar.applications list [STATUS]
python -m radar.applications add COMPANY REQ_ID TITLE
python -m radar.applications status COMPANY REQ_ID STATUS
"""

import sys
from datetime import datetime
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


def remove(company, req_id, path=None):
    """Undo a mistaken "Mark applied". Only a row still at "applied" can go; anything an email moved on stays.
    Returns the removed row, or None."""
    items = rows(path)
    for r in items:
        if r["company"] == company and r["req_id"] == req_id:
            if r["status"] != "applied":
                return None
            items.remove(r)
            write(items, path)
            return r
    return None


def add(company, req_id, title, folder="", path=None):
    """Record a new application at "applied". False when it is already recorded."""
    items = rows(path)
    if any(r["company"] == company and r["req_id"] == req_id for r in items):
        return False
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    items.append(
        {"date": now, "company": company, "title": title, "status": "applied", "folder": folder, "req_id": req_id}
    )
    write(items, path)
    return True


def main(argv):
    cmd, args = (argv[0], argv[1:]) if argv else ("list", [])
    if cmd == "list":
        shown = [r for r in rows() if not args or r["status"] == args[0]]
        for r in sorted(shown, key=lambda r: r["date"], reverse=True):
            print(f"{r['date'][:10]}  {r['status']:<9}  {r['company']} | {r['title']} | {r['req_id']}")
        print(f"{len(shown)} application(s)")
        return 0
    if cmd == "add" and len(args) == 3:
        print("recorded" if add(*args) else "already recorded")
        return 0
    if cmd == "status" and len(args) == 3:
        change = set_status(*args)
        print(
            f"{change[0]} -> {change[1]}"
            if change
            else f"no change: unknown application or status (one of {', '.join(STATUSES)})"
        )
        return 0 if change else 1
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main(sys.argv[1:]))
