"""Rows and the posting drawer carry the fit factors; a verdict stored before factors existed carries none."""

import importlib
import io
import sys

import pytest

from radar import fit


@pytest.fixture
def server(monkeypatch):
    with monkeypatch.context() as patch:  # CLI modules reconfigure stdout on import; keep pytest's stream as it is
        patch.setattr(sys, "stdout", io.TextIOWrapper(io.BytesIO(), encoding="utf-8"))
        return importlib.import_module("server")


def posting(req_id, verdict):
    return {
        "company": "GM",
        "req_id": req_id,
        "title": "Data Engineer",
        "location": "US - Remote",
        "posted_on": "Posted Today",
        "url": f"https://gm.example/{req_id}",
        "sponsorship": "likely",
        "description": "The base salary range is $120,000 - $150,000 per year.",
        "verdict": verdict,
    }


NEW = {
    "factors": [
        {"factor": n, "verdict": "partial", "posting": "ask", "resume": "", "note": ""} for n in fit.MODEL_FACTORS
    ],
    "score_entry": 4,
    "score_experienced": 3,
    "why": "Pipelines match.",
}
OLD = {"score_entry": 3, "score_experienced": 3, "why": "Stored before factors existed."}


def test_row_carries_seven_factors_for_a_new_verdict(server):
    rows = server.row(posting("R1", NEW))["factors"]
    assert [r["factor"] for r in rows] == [*fit.MODEL_FACTORS, "sponsorship", "location", "pay"]
    assert rows[-1]["posting"] == "$120k to $150k" and rows[-2]["note"] == "Remote work is offered."


def test_row_for_an_old_verdict_has_no_factors_and_the_rest_unchanged(server):
    r = server.row(posting("R2", OLD))
    assert r["factors"] == []
    assert (r["score_entry"], r["why"], r["salary"]["text"]) == (3, "Stored before factors existed.", "$120k to $150k")


def test_posting_endpoint_includes_the_factors(server, monkeypatch):
    monkeypatch.setattr(server, "jobs_all", lambda: [posting("R1", NEW), posting("R2", OLD)])
    assert len(server.posting("GM", "R1")["factors"]) == 7
    old = server.posting("GM", "R2")
    assert old["factors"] == [] and old["description"].startswith("The base salary")
