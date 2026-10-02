"""The agents as chat tools: the assistant gets what was written, or one application's prep written on the spot.
Offline: the model is a stand-in."""

import pytest

from radar import agentchat, agents, applications, chat, prep

PREP = {
    "role": "A data role.",
    "focus": [],
    "questions": [{"question": "Why us?", "kind": "motivation", "answer_from": "Say why."}] * 6,
    "stories": [{"title": "One", "situation": "s", "task": "t", "action": "a", "result": "r"}],
    "gaps": [],
    "ask_them": [],
    "work_authorization": "Plainly.",
}


@pytest.fixture
def home(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(prep.resumes, "bases", lambda: {"entry": "Resume.", "experienced": "Resume."})
    monkeypatch.setattr(prep.resumes, "profile_text", lambda: "Profile.")
    monkeypatch.setattr(prep.skills, "load", lambda: [])
    monkeypatch.setattr(prep.sponsormap, "records", lambda: {})
    calls = []
    monkeypatch.setattr(
        agents.llm, "complete", lambda system, user, schema, max_tokens=0: calls.append(user) or (PREP, "m")
    )
    monkeypatch.setattr(agents.score, "load_api_key", lambda required=True: "k")
    applications.write(
        [
            {"date": "2026-09-01 09:00", "company": "Contoso", "title": "Analyst", "status": "applied", "req_id": "R5"},
            {
                "date": "2026-09-02 09:00",
                "company": "Contoso",
                "title": "Data Scientist",
                "status": "interview",
                "req_id": "R1",
            },
        ]
    )
    return calls


def test_the_assistant_has_the_four_agents_as_tools():
    names = [t["name"] for t in chat.TOOLS]
    assert {"interview_prep", "follow_ups", "skill_gaps", "sponsor_map"} <= set(names)
    assert len(names) == len(set(names))


def test_asked_for_a_prep_it_writes_one_for_the_interview_only_and_then_reuses_it(home):
    first = chat.server_tool("interview_prep", {"company": "contoso"}, hooks={})
    assert first["text"].startswith("Interview prep: Data Scientist at Contoso, for the interview")
    assert len(home) == 1 and "requisition R1" in home[0]
    again = chat.server_tool("interview_prep", {"company": "Contoso"}, hooks={})
    assert again == first and len(home) == 1


def test_without_a_key_or_an_application_it_says_so(home, monkeypatch):
    assert agentchat.page("prep", "Northwind") == "no application at Northwind on the Applied list"
    monkeypatch.setattr(agents.score, "load_api_key", lambda required=True: None)
    assert agentchat.page("prep", "Contoso").startswith("no API key, so nothing was written")


def test_skill_gaps_and_the_sponsor_map_come_back_as_plain_lines(home, monkeypatch):
    monkeypatch.setattr(agentchat.sponsormap, "records", lambda: {})
    assert chat.server_tool("skill_gaps", {}, hooks={})["lines"][0].startswith("No skill is missing")
    assert chat.server_tool("sponsor_map", {}, hooks={})["lines"][0].startswith("No postings since")
