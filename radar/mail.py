"""python -m radar.mail: read hiring emails over IMAP and move application statuses forward.

Read-only: the folder is opened with EXAMINE and bodies are fetched with BODY.PEEK, so nothing is marked read,
moved or deleted. Needs GMAIL_ADDRESS and GMAIL_APP_PASSWORD (a Google app password) in the environment or .env.
State lives in .cache/ui/mail.json: message ids already seen, recent updates, and the needs-review list."""

import email
import html
import imaplib
import json
import os
import re
import sys
from datetime import datetime, timedelta
from email.policy import default
from email.utils import parseaddr, parsedate_to_datetime
from pathlib import Path
from urllib.parse import quote

from radar import applications, mailmatch

STATE = Path(".cache/ui/mail.json")
HOST, FOLDER, MAX_BODY = "imap.gmail.com", '"[Gmail]/All Mail"', 200_000


def env(name):
    if os.environ.get(name):
        return os.environ[name]
    if Path(".env").exists():
        for raw in Path(".env").read_text(encoding="utf-8").splitlines():
            key, _, value = raw.strip().partition("=")
            if key == name:
                return value.strip().strip('"').strip("'")
    return None


def load():
    s = json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {}
    return {
        "seen": s.get("seen", []),
        "events": s.get("events", []),
        "review": s.get("review", []),
        "last_sync": s.get("last_sync"),
    }


def save(state):
    STATE.parent.mkdir(parents=True, exist_ok=True)
    state["events"] = state["events"][-200:]
    STATE.write_text(json.dumps(state, indent=1), encoding="utf-8")


def text_of(msg):
    """Plain text of an email: the text part if there is one, else the HTML with tags removed."""
    part = msg.get_body(preferencelist=("plain", "html"))
    body = part.get_content() if part else ""
    if part is not None and part.get_content_type() == "text/html":
        body = html.unescape(re.sub(r"<(style|script)[^>]*>.*?</\1>|<[^>]+>", " ", body, flags=re.S | re.I))
    return re.sub(r"[ \t\r\f\v]+", " ", body).strip()


def gmail_link(message_id):
    return "https://mail.google.com/mail/u/0/#search/" + quote("rfc822msgid:" + message_id.strip("<>"))


def fetch(address, password, since, seen):
    """New messages since a date, excluding ones already seen and ones sent by the owner. Yields dicts."""
    box = imaplib.IMAP4_SSL(HOST)
    try:
        box.login(address, password)
        box.select(FOLDER, readonly=True)
        _, data = box.uid("SEARCH", None, "SINCE", since.strftime("%d-%b-%Y"))
        uids = data[0].split() if data and data[0] else []
        for uid in uids:
            _, head = box.uid("FETCH", uid, "(BODY.PEEK[HEADER.FIELDS (MESSAGE-ID FROM)])")
            h = email.message_from_bytes(head[0][1], policy=default) if head and head[0] else None
            mid = h and h.get("Message-ID")
            if not mid or mid in seen or parseaddr(h.get("From", ""))[1].lower() == address.lower():
                continue
            _, raw = box.uid("FETCH", uid, f"(BODY.PEEK[]<0.{MAX_BODY}>)")
            msg = email.message_from_bytes(raw[0][1], policy=default)
            when = msg.get("Date")
            yield {
                "message_id": mid,
                "sender": msg.get("From", ""),
                "subject": msg.get("Subject", ""),
                "date": parsedate_to_datetime(when).strftime("%Y-%m-%d %H:%M") if when else "",
                "body": text_of(msg),
            }
    finally:
        try:
            box.logout()
        except Exception:
            pass


def sync(messages=None):
    """Apply every new message. messages defaults to a live IMAP fetch; tests pass a list instead."""
    state, apps = load(), applications.rows()
    if messages is None:
        # Google shows app passwords as four groups of four; the spaces are display only.
        address, password = env("GMAIL_ADDRESS"), (env("GMAIL_APP_PASSWORD") or "").replace(" ", "")
        if not (address and password):
            return {"configured": False, "updated": 0, "review": 0}
        first = min((a["date"][:10] for a in apps), default=datetime.now().strftime("%Y-%m-%d"))
        messages = fetch(
            address, password, datetime.strptime(first, "%Y-%m-%d") - timedelta(days=1), set(state["seen"])
        )
    updated = review = 0
    for m in messages:
        state["seen"].append(m["message_id"])
        d = mailmatch.decide(m, apps)
        if not d:
            continue
        item = {k: m[k] for k in ("message_id", "date", "sender", "subject")} | {
            "snippet": m["body"][:240],
            "link": gmail_link(m["message_id"]),
            **d,
        }
        if d["action"] == "update":
            change = applications.set_status(d["company"], d["req_id"], d["status"], forward_only=True)
            if change:  # no change when the email is older news than the current status
                state["events"].append(item | {"from_status": change[0]})
                updated += 1
                apps = applications.rows()
        else:
            state["review"].append(item)
            review += 1
    state["last_sync"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    save(state)
    return {"configured": True, "updated": updated, "review": review}


def resolve(message_id, company=None, req_id=None, status=None):
    """Settle a needs-review item: set the chosen status (any direction, it is Rohan's call) or just dismiss it."""
    state = load()
    item = next((r for r in state["review"] if r["message_id"] == message_id), None)
    state["review"] = [r for r in state["review"] if r["message_id"] != message_id]
    if item and company and req_id and status:
        change = applications.set_status(company, req_id, status)
        if change:
            state["events"].append(
                item
                | {
                    "company": company,
                    "req_id": req_id,
                    "status": status,
                    "from_status": change[0],
                    "reason": "reviewed",
                }
            )
    save(state)
    return {"ok": True}


def main():
    result = sync()
    if not result["configured"]:
        print("mail: off (add GMAIL_ADDRESS and GMAIL_APP_PASSWORD to .env to turn it on)")
        return
    print(f"mail: {result['updated']} status updates, {result['review']} emails need review")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
