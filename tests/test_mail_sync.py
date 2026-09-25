"""Mail sync: forward-only updates, review list, and a read-only IMAP fetch that never marks mail read."""

from datetime import datetime
from email.message import EmailMessage

from radar import applications, mail


def setup(tmp_path, monkeypatch, status="applied"):
    monkeypatch.setattr(applications, "PATH", tmp_path / "applications.md")
    monkeypatch.setattr(mail, "STATE", tmp_path / "mail.json")
    row = {"date": "2026-09-20 10:00", "company": "Capital One", "title": "AI Engineer 3", "status": status}
    applications.write([row | {"folder": "", "req_id": "R1001740"}])


def msg(mid, subject, body):
    return {
        "message_id": mid,
        "sender": "capitalone@myworkday.com",
        "subject": subject,
        "date": "2026-09-24 09:00",
        "body": body,
    }


def test_sync_moves_forward_and_records_the_email(tmp_path, monkeypatch):
    setup(tmp_path, monkeypatch)
    r = mail.sync([msg("<a@x>", "Interview", "We would like to interview you for R1001740.")])
    assert r == {"configured": True, "updated": 1, "review": 0}
    assert applications.rows()[0]["status"] == "interview"
    event = mail.load()["events"][0]
    assert event["from_status"] == "applied" and event["link"].startswith("https://mail.google.com/")


def test_older_news_never_moves_a_status_back(tmp_path, monkeypatch):
    setup(tmp_path, monkeypatch, status="interview")
    r = mail.sync([msg("<b@x>", "Thank you for applying", "We received your application R1001740.")])
    assert r["updated"] == 0 and applications.rows()[0]["status"] == "interview"


def test_review_then_resolve_or_dismiss(tmp_path, monkeypatch):
    setup(tmp_path, monkeypatch)
    mail.sync(
        [
            msg("<c@x>", "Capital One update", "We regret to inform you."),
            msg("<d@x>", "Capital One news", "The position has been filled."),
        ]
    )
    assert [r["message_id"] for r in mail.load()["review"]] == ["<c@x>", "<d@x>"]
    mail.resolve("<c@x>", "Capital One", "R1001740", "rejected")
    mail.resolve("<d@x>")
    assert mail.load()["review"] == [] and applications.rows()[0]["status"] == "rejected"


def test_off_until_credentials_exist(tmp_path, monkeypatch):
    setup(tmp_path, monkeypatch)
    monkeypatch.setattr(mail, "env", lambda name: None)
    assert mail.sync()["configured"] is False


class FakeIMAP:
    def __init__(self, raws):
        self.raws, self.calls = raws, []

    def __call__(self, host):
        return self

    def login(self, user, password):
        self.calls.append(("login", user))

    def select(self, folder, readonly=False):
        self.calls.append(("select", folder, readonly))

    def uid(self, cmd, *args):
        self.calls.append((cmd, *args))
        if cmd == "SEARCH":
            return "OK", [b" ".join(str(i).encode() for i in range(len(self.raws)))]
        return "OK", [(b"", self.raws[int(args[0])])]

    def logout(self):
        pass


def raw(mid, sender, subject, html):
    m = EmailMessage()
    m["Message-ID"], m["From"], m["Subject"], m["Date"] = mid, sender, subject, "Thu, 24 Sep 2026 09:00:00 -0400"
    m.set_content(html, subtype="html")
    return m.as_bytes()


def test_fetch_is_read_only_and_skips_seen_and_own_mail(monkeypatch):
    fake = FakeIMAP(
        [
            raw("<new@x>", "HR <hr@myworkday.com>", "Interview", "<p>Interview for <b>R1001740</b></p>"),
            raw("<seen@x>", "HR <hr@myworkday.com>", "Old", "<p>old</p>"),
            raw("<mine@x>", "me@gmail.com", "Sent", "<p>mine</p>"),
        ]
    )
    monkeypatch.setattr(mail.imaplib, "IMAP4_SSL", fake)
    got = list(mail.fetch("me@gmail.com", "app-password", datetime(2026, 9, 13), {"<seen@x>"}))
    assert [m["message_id"] for m in got] == ["<new@x>"]
    assert "R1001740" in got[0]["body"] and "<b>" not in got[0]["body"]
    assert ("select", mail.FOLDER, True) in fake.calls
    fetches = [c[2] for c in fake.calls if c[0] == "FETCH"]
    assert fetches and all("PEEK" in f for f in fetches)


def test_app_password_is_used_without_display_spaces(tmp_path, monkeypatch):
    setup(tmp_path, monkeypatch)
    values = {"GMAIL_ADDRESS": "me@gmail.com", "GMAIL_APP_PASSWORD": "abcd efgh ijkl mnop"}
    monkeypatch.setattr(mail, "env", values.get)
    used = {}
    monkeypatch.setattr(mail, "fetch", lambda address, password, since, seen: used.update(password=password) or [])
    assert mail.sync()["configured"] is True
    assert used["password"] == "abcdefghijklmnop"
