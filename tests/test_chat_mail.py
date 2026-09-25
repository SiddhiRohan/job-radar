"""The chat assistant can check mail through a server hook."""

import importlib
import io
import sys

from radar import chat


def test_check_mail_is_a_tool_and_goes_to_its_hook():
    tool = next(t for t in chat.TOOLS if t["name"] == "check_mail")
    assert tool["input_schema"] == {"type": "object", "properties": {}}
    calls = []
    out = chat.server_tool("check_mail", {}, {"check_mail": lambda args: calls.append(args) or {"updated": 1}})
    assert out == {"updated": 1} and calls == [{}]


def test_server_hook_reports_counts_and_review_items(monkeypatch):
    with monkeypatch.context() as patch:
        patch.setattr(sys, "stdout", io.TextIOWrapper(io.BytesIO(), encoding="utf-8"))
        server = importlib.import_module("server")
    monkeypatch.setattr(server.mail, "sync", lambda: {"configured": True, "updated": 2, "review": 1})
    item = {
        "sender": "HR",
        "subject": "Update",
        "status": "rejected",
        "company": None,
        "reason": "no req id",
        "snippet": "x",
    }
    monkeypatch.setattr(server.mail, "load", lambda: {"review": [item]})
    out = server.check_mail_for({})
    assert out["updated"] == 2 and out["needs_review_total"] == 1
    assert "snippet" not in out["needs_review"][0]  # the assistant gets the subject, not the email text
