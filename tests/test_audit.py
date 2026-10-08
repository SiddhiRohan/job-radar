"""The filter auditor: a weekly sample of what the rules dropped, judged by the model; suggested changes checked
before they are kept and made in config.json only when applied. Offline: the model is a stand-in."""

import json
from datetime import datetime
from pathlib import Path

import pytest

from radar import agentchat, agentcli, agents, audit, dropped

TODAY = datetime.now()
CFG = {"title_patterns": ["data scien"], "exclude_seniority": ["staff", "lead"], "exclude_domain": [], "agents": {}}


def answer(**over):
    a = {
        "summary": "The filters are close; one pattern would bring back applied scientist roles.",
        "wanted": [
            {"id": "r1", "why": "Applied science is the same work."},
            {"id": "r99", "why": "Not in the sample."},
        ],
        "changes": [
            {
                "setting": "title_patterns",
                "action": "add",
                "value": "applied scien",
                "why": "Keeps r1.",
                "keeps": ["r1"],
            },
            {
                "setting": "exclude_seniority",
                "action": "remove",
                "value": "principal",
                "why": "Not there.",
                "keeps": [],
            },
            {"setting": "title_patterns", "action": "add", "value": "(broken", "why": "Bad pattern.", "keeps": []},
        ],
    }
    return a | over


@pytest.fixture
def home(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    Path("config.json").write_text(json.dumps(CFG, indent=2) + "\n", encoding="utf-8")
    monkeypatch.setattr(audit.resumes, "profile_text", lambda: "Targets data science roles.")
    calls = []
    monkeypatch.setattr(
        agents.llm, "complete", lambda system, user, schema, max_tokens=0: calls.append(user) or (answer(), "m")
    )
    monkeypatch.setattr(agents.score, "load_api_key", lambda required=True: "k")
    rows = [dropped.item(f"Co{n}", {"title": "Applied Scientist", "req_id": f"R{n}"}, "off_target") for n in range(3)]
    rows += [dropped.item(f"Co{n}", {"title": f"Recruiter {n}", "req_id": f"X{n}"}, "off_target") for n in range(17)]
    rows += [dropped.item("Contoso", {"title": "Staff Data Scientist", "req_id": "S1"}, "seniority")]
    dropped.record(rows, when=TODAY)
    return calls


def test_an_audit_is_due_weekly_once_enough_was_dropped(home, tmp_path):
    assert len(audit.due(CFG)) == 1
    agents.run(["audit"])
    assert audit.due(CFG) == [] and len(audit.due(CFG, every=True)) == 1  # a week has not passed; on demand it runs
    Path(dropped.LOG).unlink()
    Path(audit.STATE).unlink()
    assert audit.due(CFG) == []  # nothing dropped: nothing to audit


def test_the_sample_lists_each_title_once_with_its_rule_and_count(home):
    jobs = [
        {
            "company": "Fabrikam",
            "req_id": "F1",
            "title": "Data Scientist",
            "first_seen": TODAY.isoformat(),
            "sponsorship": "no",
        }
        | {"sponsorship_evidence": "US citizens only.", "url": ""}
    ]
    p = audit.packet(audit.due(CFG)[0], jobs=jobs)
    text = audit.prompt(p)
    assert "r1 | off_target | 3 posting(s) | Applied Scientist | Co0" in text
    assert "| sponsorship_no | 1 posting(s) | Data Scientist | Fabrikam | US citizens only." in text
    assert '"exclude_seniority": [\n  "staff",\n  "lead"\n ]' in text and "Targets data science roles." in text


def test_only_sound_changes_and_known_postings_are_kept(home):
    agents.run(["audit"], ("", None))
    r = audit.report()
    assert [w["title"] for w in r["wanted"]] == ["Applied Scientist"] and r["wanted"][0]["why"].startswith("Applied")
    assert [c["value"] for c in r["changes"]] == ["applied scien"]
    assert r["notes"] == [
        "r99 is not an item in the sample",
        "left out: exclude_seniority has no entry 'principal' to remove",
        "left out: '(broken' is not a valid pattern",
    ]
    assert r["dropped"] == {"off_target": 20, "seniority": 1}


def test_a_change_is_made_only_when_applied_and_only_once(home):
    agents.run(["audit"], ("", None))
    assert json.loads(Path("config.json").read_text(encoding="utf-8"))["title_patterns"] == ["data scien"]
    assert audit.apply(0) == "title_patterns: added applied scien"
    cfg = json.loads(Path("config.json").read_text(encoding="utf-8"))
    assert cfg["title_patterns"] == ["data scien", "applied scien"] and cfg["exclude_seniority"] == ["staff", "lead"]
    assert audit.apply(0) == "nothing to apply" and audit.apply(7) == "nothing to apply"


def test_the_chat_and_the_terminal_reach_the_audit(home, capsys):
    text = agentchat.call("filter_audit", {})["text"]
    assert text.startswith("Filter audit, ") and '1. title_patterns: add "applied scien". Keeps r1.' in text
    assert len(home) == 1 and agentchat.call("filter_audit", {})["text"] == text  # shown again, not rewritten
    assert agentcli.main(["audit", "apply", "1"]) == 0
    assert "title_patterns: added applied scien" in capsys.readouterr().out
    assert "Applied." in agentchat.call("filter_audit", {})["text"]


def test_without_a_key_nothing_is_written(home, monkeypatch):
    monkeypatch.setattr(agents.score, "load_api_key", lambda required=True: None)
    assert agentchat.audit_page().startswith("no API key, so no audit was written")
    assert audit.load() == {}
