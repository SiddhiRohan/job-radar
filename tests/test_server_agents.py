"""The Agents page's routes: one call for everything the agents wrote and found, a run, and marking a draft sent."""

import importlib
import io
import sys

import pytest
from fastapi import HTTPException


@pytest.fixture
def server(tmp_path, monkeypatch):
    with monkeypatch.context() as patch:  # CLI modules reconfigure stdout on import; keep pytest's stream as it is
        patch.setattr(sys, "stdout", io.TextIOWrapper(io.BytesIO(), encoding="utf-8"))
        module = importlib.import_module("server")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(module, "jobs_all", lambda: [])
    monkeypatch.setattr(module.sponsormap, "records", lambda: {})
    monkeypatch.setattr(module.gaps.skills, "load", lambda: [])
    monkeypatch.setattr(module.agents, "has_key", lambda: False)
    return module


def test_one_call_brings_every_agents_report(server):
    r = server.agent_reports()
    assert set(r) == {"key", "prep", "followups", "gaps", "sponsors"}
    assert r["key"] is False and r["prep"] == {"items": [], "due": 0} and r["followups"] == {"items": [], "due": 0}
    assert r["gaps"]["skills"] == [] and r["sponsors"]["employers"] == []


def test_a_run_from_the_page_names_the_agent_and_the_application(server, monkeypatch):
    seen = []
    monkeypatch.setattr(server.agents, "run", lambda names, who: seen.append((names, who)) or {})
    monkeypatch.setattr(server, "background", lambda fn, *args: fn(*args))
    server.agent_run({"name": "prep", "company": "Contoso", "req_id": "R1"})
    server.agent_run({})
    assert seen == [(["prep"], ("Contoso", "R1")), (None, None)]


def test_marking_a_draft_that_does_not_exist_is_refused(server):
    with pytest.raises(HTTPException) as e:
        server.followup_done({"key": "Contoso|R1"})
    assert e.value.status_code == 404
