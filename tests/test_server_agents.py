"""The Agents page's routes: one call for everything the agents wrote and found, a run, and marking a draft sent."""

import importlib
import io
import sys

import pytest
from fastapi import HTTPException

from radar import runlock


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
    assert set(r) == {
        "key",
        "waiting",
        "followup_after_days",
        "prep",
        "debriefs",
        "audit",
        "followups",
        "gaps",
        "sponsors",
    }
    assert (
        r["key"] is False
        and r["waiting"] == {"prep": 0, "followups": 0, "debrief": 0, "audit": 0}
        and r["followup_after_days"] == 10
    )
    assert r["prep"] == {"items": []} and r["followups"] == {"items": []}
    assert r["gaps"]["skills"] == [] and r["sponsors"]["employers"] == []


def test_a_run_from_the_page_names_the_agent_and_the_application(server, monkeypatch):
    seen = []
    monkeypatch.setattr(server.agents, "run", lambda names, who: seen.append((names, who)) or {})
    monkeypatch.setattr(server, "background", lambda fn, *args: fn(*args))
    with pytest.raises(HTTPException) as e:  # no API key: nothing would be written
        server.agent_run({})
    assert e.value.status_code == 409 and "No API key" in e.value.detail
    monkeypatch.setattr(server.agents, "has_key", lambda: True)
    server.agent_run({"name": "prep", "company": "Contoso", "req_id": "R1"})
    server.agent_run({})
    assert seen == [(["prep"], ("Contoso", "R1")), (None, None)]
    runlock.LOCK.parent.mkdir(parents=True, exist_ok=True)
    runlock.LOCK.write_text("{}", encoding="utf-8")  # the morning run is going
    with pytest.raises(HTTPException) as e:
        server.agent_run({})
    assert "morning run is going" in e.value.detail and len(seen) == 2


def test_marking_a_draft_that_does_not_exist_is_refused(server):
    with pytest.raises(HTTPException) as e:
        server.followup_done({"key": "Contoso|R1"})
    assert e.value.status_code == 404


def test_an_interview_account_is_kept_even_without_a_key(server, monkeypatch):
    server.applications.add("Contoso", "R1", "Analytics Engineer")
    kept = server.debrief_add({"company": "Contoso", "req_id": "R1", "account": "They asked about dbt."})
    assert kept["kept"] is True and "No API key" in kept["note"]
    assert server.debrief.load()["Contoso|R1"][0]["account"] == "They asked about dbt."
    with pytest.raises(HTTPException) as e:
        server.debrief_add({"company": "Contoso", "req_id": "R1", "account": " "})
    assert e.value.status_code == 400
    seen = []
    monkeypatch.setattr(server.agents, "has_key", lambda: True)
    monkeypatch.setattr(server.agents, "run", lambda names, who: seen.append((names, who)) or {})
    monkeypatch.setattr(server, "background", lambda fn, *args: fn(*args))
    server.debrief_add({"company": "Contoso", "req_id": "R1", "account": "And about Airflow."})
    assert seen == [(["debrief"], ("Contoso", "R1"))]


def test_the_audit_runs_from_the_page_and_a_change_applies_by_number(server, monkeypatch):
    with pytest.raises(HTTPException) as e:  # no API key: nothing would be written
        server.audit_run()
    assert e.value.status_code == 409
    seen = []
    monkeypatch.setattr(server.agents, "has_key", lambda: True)
    monkeypatch.setattr(server.agents, "run", lambda names, who: seen.append((names, who)) or {})
    monkeypatch.setattr(server, "background", lambda fn, *args: fn(*args))
    server.audit_run()
    assert seen == [(["audit"], ("", None))]
    assert server.audit_apply({"n": 0}) == {"result": "nothing to apply"}
