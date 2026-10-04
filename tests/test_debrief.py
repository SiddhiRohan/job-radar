"""Interview debrief: accounts kept by round, debriefs written from them, and the next prep reading what they found.
Offline: the model is a stand-in that returns a fixed debrief."""

import io

import pytest

from radar import agentchat, agentcli, agents, applications, debrief, prep

RESUME = "Built a retrieval chatbot used by 2,000 people. Rebuilt the lending marts in dbt."
ACCOUNT = (
    "Screen with Sam. They asked why I left and about dbt tests; I rambled on the second. I said we cut costs 30%."
)


def answer(**over):
    a = {
        "summary": "It went well; the next step depends on the dbt depth.",
        "asked": [
            {"question": "Why are you looking?", "went": "strong", "better": ""},
            {
                "question": "How do you test dbt models?",
                "went": "weak",
                "better": "Say how you tested every model in the marts.",
            },
        ],
        "concerns": [{"concern": "Depth in dbt testing.", "address": "Name the tests you wrote."}],
        "went_well": ["Clear motivation."],
        "next_round": ["Practise a dbt walkthrough."],
        "owed": ["Send the project link."],
        "thank_you_subject": "Thank you for today",
        "thank_you_body": " ".join(["thanks"] * 70),
    }
    return a | over


@pytest.fixture
def home(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(debrief.resumes, "bases", lambda: {"entry": RESUME, "experienced": RESUME})
    monkeypatch.setattr(debrief.resumes, "profile_text", lambda: "Targets data roles.")
    monkeypatch.setattr(debrief.skills, "load", lambda: [])
    monkeypatch.setattr(prep.sponsormap, "records", lambda: {})
    calls = []
    monkeypatch.setattr(
        agents.llm, "complete", lambda system, user, schema, max_tokens=0: calls.append(user) or (answer(), "m")
    )
    monkeypatch.setattr(agents.score, "load_api_key", lambda required=True: "k")
    applications.add("Contoso", "R1", "Analytics Engineer")
    applications.set_status("Contoso", "R1", "screen")
    applications.add("Northwind", "R2", "Data Scientist")
    return calls


def test_an_account_waits_for_its_debrief_and_a_second_one_adds_to_it(home):
    assert debrief.add("Contoso", "R1", ACCOUNT)
    assert debrief.add("Contoso", "R1", "Also: they asked about Airflow.")
    (r,) = debrief.load()["Contoso|R1"]
    assert r["account"].endswith("Also: they asked about Airflow.") and r["stage"] == "screen" and r["debrief"] is None
    assert [i["key"] for i in debrief.due()] == ["Contoso|R1"]
    assert not debrief.add("Contoso", "R9", ACCOUNT) and not debrief.add("Contoso", "R1", "   ")


def test_a_debrief_is_written_from_the_account_and_numbers_said_in_it_stay(home):
    debrief.add("Contoso", "R1", ACCOUNT)
    r = agents.run(["debrief"])
    assert r["debrief"]["made"] == ["Contoso|R1"] and "THEIR ACCOUNT OF IT:\nScreen with Sam." in home[0]
    clean, notes = debrief.facts.lock({"x": "cut costs 30% and 45%"}, [ACCOUNT])
    assert clean == {"x": "cut costs 30% and [?]%"} and len(notes) == 1  # what they said counts; nothing else does
    assert debrief.due() == [] and [i["key"] for i in debrief.due(every=True)] == ["Contoso|R1"]


def test_the_next_round_and_the_next_prep_read_what_earlier_rounds_found(home):
    debrief.add("Contoso", "R1", ACCOUNT)
    agents.run(["debrief"])
    applications.set_status("Contoso", "R1", "interview")
    debrief.add("Contoso", "R1", "Panel interview: they asked about Airflow retries.")
    assert len(debrief.load()["Contoso|R1"]) == 2  # a new round, not an addition to the written one
    earlier = debrief.earlier("Contoso|R1", before=-1)
    assert (
        "answers to work on: How do you test dbt models?" in earlier and "They seemed unsure: Depth in dbt" in earlier
    )
    p = prep.packet(prep.due()[0], jobs=[], recs={})
    assert "EARLIER ROUNDS, FROM THEIR DEBRIEFS (weight these):\nRound 1, the screen" in prep.prompt(p)


def test_the_report_lists_rounds_newest_first_and_counts_what_waits(home):
    debrief.add("Contoso", "R1", ACCOUNT)
    agents.run(["debrief"])
    debrief.add("Contoso", "R1", "Second round notes.")
    r = debrief.report()
    assert [(x["company"], x["round"]) for x in r["items"]] == [("Contoso", 1)] and r["waiting"] == 1
    page = agentchat.agentview.text("debrief", "Contoso")
    assert page.startswith("Interview debrief: Analytics Engineer at Contoso, the screen on ")
    assert "2. How do you test dbt models? (weak) Try saying: Say how you tested" in page
    assert "You said you would send:\n- Send the project link." in page


def test_the_chat_keeps_the_account_writes_once_and_then_shows_it(home, monkeypatch):
    out = agentchat.call("interview_debrief", {"company": "contoso", "account": ACCOUNT})["text"]
    assert out.startswith("Interview debrief: Analytics Engineer at Contoso") and len(home) == 1
    again = agentchat.call("interview_debrief", {"company": "Contoso"})["text"]
    assert again == out and len(home) == 1
    assert agentchat.debrief_page("Fabrikam", account="x") == "no application at Fabrikam on the Applied list"
    monkeypatch.setattr(agents.score, "load_api_key", lambda required=True: None)
    assert agentchat.debrief_page("Northwind", account=ACCOUNT).startswith("kept your account; with no API key")
    assert [i["key"] for i in debrief.due()] == ["Northwind|R2"]  # it waits for a key or a coding assistant


def test_the_terminal_reads_the_account_from_standard_input(home, capsys):
    assert agentcli.main(["debrief", "Contoso"], stdin=io.StringIO(ACCOUNT)) == 0
    assert "kept your account of Analytics Engineer at Contoso" in capsys.readouterr().out
    assert debrief.load()["Contoso|R1"][0]["debrief"]["summary"].startswith("It went well")
    assert agentcli.main(["debrief", "Contoso"], stdin=io.StringIO("")) == 1


def test_a_thank_you_note_out_of_length_goes_back(home):
    assert debrief.check(answer()) == []
    assert debrief.check(answer(thank_you_body="Thanks.")) == ["thank_you_body is 1 words; write 60 to 120"]
