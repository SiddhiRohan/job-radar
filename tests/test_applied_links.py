"""The Applied API joins each application to its posting URL so the page can link the title."""

import importlib
import io
import sys


def load_server(monkeypatch):
    with monkeypatch.context() as patch:
        patch.setattr(sys, "stdout", io.TextIOWrapper(io.BytesIO(), encoding="utf-8"))
        return importlib.import_module("server")


def test_applications_carry_their_posting_url(monkeypatch):
    server = load_server(monkeypatch)
    apps = [
        {
            "date": "2026-09-20 10:00",
            "company": "GM",
            "title": "Data Engineer",
            "status": "applied",
            "folder": "",
            "req_id": "R1",
        },
        {
            "date": "2026-09-21 10:00",
            "company": "Visa",
            "title": "Data Scientist",
            "status": "screen",
            "folder": "",
            "req_id": "R9",
        },
    ]
    jobs = [{"company": "GM", "req_id": "R1", "url": "https://gm.example/R1"}]
    monkeypatch.setattr(server, "applied_rows", lambda: apps)
    monkeypatch.setattr(server, "jobs_all", lambda: jobs)
    rows = server.applied()
    assert [r["req_id"] for r in rows] == ["R9", "R1"]  # newest first
    assert rows[1]["url"] == "https://gm.example/R1"
    assert rows[0]["url"] is None  # no stored posting: the page shows plain text
