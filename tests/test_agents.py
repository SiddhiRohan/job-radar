"""The agents runner: the API writes when a key is set, a coding assistant answers task files when not. Offline: the
model is a stand-in that returns fixed answers."""

import json
from datetime import datetime
from pathlib import Path

import pytest

from radar import agents, agenttasks, agentview, applications, followup, prep

NOW = datetime.now().strftime("%Y-%m-%d %H:%M")
PREP = {
    "role": "A data role.",
    "focus": [{"topic": "Pipelines", "why": "The posting leads with them.", "evidence": "Built 3 pipelines."}],
    "questions": [{"question": "Why us?", "kind": "motivation", "answer_from": "The pipelines."}] * 6,
    "stories": [{"title": "Pipelines", "situation": "s", "task": "t", "action": "a", "result": "r"}],
    "gaps": [],
    "ask_them": ["What comes first?"],
    "work_authorization": "Say it plainly.",
}
NOTE = {
    "linkedin_note": "I applied for the ML Engineer role (R2).",
    "email_subject": "ML Engineer, R2",
    "email_body": " ".join(["word"] * 70),
    "search_hint": "Northwind recruiter",
}


@pytest.fixture
def home(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    for mod in (prep, followup):
        monkeypatch.setattr(
            mod.resumes, "bases", lambda: {"entry": "Built 3 pipelines.", "experienced": "Built 3 pipelines."}
        )
    monkeypatch.setattr(prep.resumes, "profile_text", lambda: "Targets data roles.")
    monkeypatch.setattr(prep.skills, "load", lambda: [])
    monkeypatch.setattr(prep.sponsormap, "records", lambda: {})
    applications.write(
        [
            {
                "date": "2020-01-01 09:00",
                "company": "Contoso",
                "title": "Data Engineer",
                "status": "applied",
                "req_id": "R5",
            },
            {
                "date": "2020-01-02 09:00",
                "company": "Contoso",
                "title": "Data Scientist",
                "status": "interview",
                "req_id": "R1",
            },
            {
                "date": "2020-01-03 09:00",
                "company": "Northwind",
                "title": "ML Engineer",
                "status": "applied",
                "req_id": "R2",
            },
            {"date": NOW, "company": "Fabrikam", "title": "Analyst", "status": "applied", "req_id": "R3"},
        ]
    )
    Path("config.json").write_text(json.dumps({"agents": {"followups": True}}), encoding="utf-8")
    return tmp_path


def model(*answers):
    """A stand-in for llm.complete: prep or follow-up answers by schema, in the order given for follow-ups."""
    notes, calls = list(answers), []

    def complete(system, user, schema, max_tokens=0):
        calls.append(user)
        return (dict(notes.pop(0) if notes else NOTE) if "linkedin_note" in schema["properties"] else dict(PREP)), "m"

    complete.calls = calls
    return complete


def test_without_a_key_nothing_is_written_and_the_work_waits(home):
    r = agents.run(key="")
    assert {k: (v["made"], v["waiting"]) for k, v in r.items()} == {"prep": ([], 1), "followups": ([], 2)}
    assert prep.load() == {} and followup.load() == {}


def test_with_a_key_each_agent_writes_what_is_due(home):
    r = agents.run(complete=model(), key="k")
    assert r["prep"]["made"] == ["Contoso|R1"]
    assert r["followups"]["made"] == ["Contoso|R5", "Northwind|R2"]
    assert prep.load()["Contoso|R1"]["by"] == "m"
    assert followup.load()["Northwind|R2"]["draft"]["search_hint"] == "Northwind recruiter"


def test_a_draft_too_long_goes_back_once_then_is_kept_with_a_note(home):
    long = NOTE | {"linkedin_note": "x" * 320}
    fixed = agents.run(["followups"], who=("Northwind", None), complete=model(long, NOTE), key="k")
    assert fixed["followups"]["made"] == ["Northwind|R2"] and followup.load()["Northwind|R2"]["notes"] == []
    complete = model(long, long)
    agents.run(["followups"], who=("Northwind", None), complete=complete, key="k")
    assert "fix them: linkedin_note is 320 characters" in complete.calls[1]
    assert followup.load()["Northwind|R2"]["notes"] == ["linkedin_note is 320 characters; it must stay under 300"]


def test_an_agent_turned_off_does_nothing_until_asked_by_name(home):
    Path("config.json").write_text(json.dumps({"agents": {"followups": False}}), encoding="utf-8")
    assert agents.run(["followups"], complete=model(), key="k")["followups"]["made"] == []
    asked = agents.run(["followups"], who=("northwind", None), complete=model(), key="k")
    assert asked["followups"]["made"] == ["Northwind|R2"]


def test_by_name_one_application_is_chosen_from_an_exact_or_unique_name(home):
    assert [i["key"] for i in agents.todo("prep", {}, ("contoso", None))] == ["Contoso|R1"]  # the interview
    assert [i["key"] for i in agents.todo("prep", {}, ("Contoso", "R5"))] == ["Contoso|R5"]
    assert [i["key"] for i in agents.todo("prep", {}, ("North", None))] == ["Northwind|R2"]  # the only one
    assert [i["key"] for i in agents.todo("followups", {}, ("Contoso", None))] == ["Contoso|R5"]  # no reply yet
    applications.add("Contoso Health", "R7", "Analyst")
    assert agents.todo("prep", {}, ("Cont", None)) == []  # two employers start so: never guess
    assert agents.todo("prep", {}, ("ontoso", None)) == []  # not inside a name either


def test_a_failure_is_reported_and_the_run_goes_on(home, monkeypatch):
    def missing():
        raise FileNotFoundError("no resume found: put yours in Resume/")

    monkeypatch.setattr(prep.resumes, "bases", missing)
    r = agents.run(complete=model(), key="k")
    assert r["prep"]["errors"] == ["Contoso|R1: no resume found: put yours in Resume/"]
    assert [e.split(":")[0] for e in r["followups"]["errors"]] == ["Contoso|R5", "Northwind|R2"]
    assert prep.load() == {} and followup.load() == {}


def test_an_assistant_answers_the_task_file_and_save_checks_each_answer(home):
    ids = agenttasks.write()
    assert ids == ["prep:Contoso|R1", "followups:Contoso|R5", "followups:Northwind|R2"]
    packet = json.loads(agenttasks.TASKS.read_text(encoding="utf-8"))
    assert set(packet["agents"]) == {"prep", "followups"} and "schema" in packet["agents"]["prep"]
    assert "requisition R1" in packet["tasks"][0]["input"]
    stored, rejected = agenttasks.save(
        {
            "prep:Contoso|R1": PREP,
            "followups:Northwind|R2": NOTE | {"linkedin_note": 7},
            "followups:Nobody|R9": NOTE,
        }
    )
    assert stored == ["prep:Contoso|R1"] and prep.load()["Contoso|R1"]["by"] == "assistant"
    assert rejected["followups:Northwind|R2"] == ["answer.linkedin_note should be string"]
    assert rejected["followups:Nobody|R9"][0].startswith("no such task")


def test_what_the_agents_wrote_reads_as_plain_pages(home, capsys):
    agents.run(complete=model(), key="k")
    page = agentview.text("prep")
    assert page.startswith("Interview prep: Data Scientist at Contoso, for the interview, made ")
    assert "Likely questions:\n1. Why us? (motivation) The pipelines." in page
    assert page.endswith("Work authorization:\nSay it plainly.")
    assert agents.main(["show", "followups", "northwind"]) == 0
    shown = capsys.readouterr().out
    assert 'Find them on LinkedIn: search "Northwind recruiter"' in shown and "Contoso" not in shown
    assert agentview.text("prep", "Adatum") == "nothing written yet for Adatum"


def test_a_second_run_while_one_is_writing_does_nothing(home):
    with agents.BUSY:
        r = agents.run(complete=model(), key="k")
    assert r["prep"]["errors"] == ["the agents are already writing; try again shortly"]
    assert prep.load() == {} and followup.load() == {}


def test_what_waits_follows_config(home):
    assert agents.waiting({}) == {"prep": 1, "followups": 2}
    assert agents.waiting({"agents": {"prep": False, "followup_after_days": 100000}}) == {"prep": 0, "followups": 0}


def test_an_unreadable_state_file_reads_as_empty_and_the_brief_still_builds(home):
    from radar import brief

    for mod in (prep, followup):
        mod.STATE.parent.mkdir(parents=True, exist_ok=True)
        mod.STATE.write_text("{", encoding="utf-8")
        assert mod.load() == {}
    assert brief.build(jobs=[])["agents"] == []
