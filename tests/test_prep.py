"""Interview prep: which applications get one, what it is written from, and numbers kept to the resume. Offline."""

import pytest

from radar import applications, facts, prep

RESUME = "Built a retrieval chatbot used by 2,000 people. Cut report time from 3 days to 4 hours with Airflow."


@pytest.fixture
def home(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(prep.resumes, "bases", lambda: {"entry": "ENTRY " + RESUME, "experienced": RESUME})
    monkeypatch.setattr(prep.resumes, "profile_text", lambda: "Targets data science roles. F-1 OPT.")
    monkeypatch.setattr(prep.skills, "load", lambda: ["Airflow"])
    for company, req, status in (
        ("Contoso", "R1", "interview"),
        ("Northwind", "R2", "applied"),
        ("Adatum", "R3", "screen"),
    ):
        applications.add(company, req, "Data Scientist")
        applications.set_status(company, req, status)
    return tmp_path


def answer(**over):
    a = {
        "role": "A data science role on a 9 person team.",
        "focus": [
            {"topic": "Retrieval", "why": "The posting leads with it.", "evidence": "Built a retrieval chatbot."}
        ],
        "questions": [
            {"question": f"Question {i}?", "kind": "technical", "answer_from": "The chatbot."} for i in "abcd"
        ],
        "stories": [
            {
                "title": "Chatbot",
                "situation": "Support was slow.",
                "task": "Answer questions faster.",
                "action": "Built a retrieval chatbot.",
                "result": "Used by 2,000 people and cut handling time by 40%.",
            }
        ],
        "gaps": [],
        "ask_them": ["What does the first quarter look like?"],
        "work_authorization": "The posting says nothing; the employer usually sponsors.",
    }
    return a | over


def test_screens_and_interviews_are_due_and_a_new_stage_brings_a_new_prep(home):
    assert [i["company"] for i in prep.due()] == ["Contoso", "Adatum"]
    item = prep.due()[1]
    prep.store_answer(item, answer(), "test", prep.packet(item, jobs=[], recs={}))
    assert [i["company"] for i in prep.due()] == ["Contoso"]
    applications.set_status("Adatum", "R3", "interview")
    assert [i["company"] for i in prep.due()] == ["Contoso", "Adatum"]
    assert len(prep.due(every=True)) == 3  # asked for by name, any application can have one


def test_the_prep_is_written_from_the_posting_its_fit_and_the_employers_record(home):
    job = {
        "company": "Contoso",
        "req_id": "R1",
        "description": "We build retrieval systems.",
        "sponsorship": "yes",
        "sponsorship_evidence": "We sponsor visas.",
        "verdict": {
            "recommended_resume": "entry",
            "factors": [
                {"factor": "skills", "verdict": "gap", "posting": "Spark", "resume": "", "note": "Missing: Spark."}
            ],
        },
    }
    recs = {"Contoso": {"default": True, "source": "FY2025 filings", "filings": "120 LCAs"}}
    p = prep.packet(prep.due()[0], jobs=[job], recs=recs)
    assert p["resume"].startswith("ENTRY") and p["posting"] == "We build retrieval systems."
    assert p["fit"] == "- skills (gap): posting asks Spark; resume shows nothing; Missing: Spark."
    assert p["sponsorship"] == (
        'The posting reads yes: "We sponsor visas.". The employer default is likely (FY2025 filings); H-1B filings: 120 LCAs.'
    )
    text = prep.prompt(p)
    assert "now at the interview stage" in text and "CONFIRMED SKILLS:\nAirflow" in text


def test_a_posting_that_was_never_stored_still_gets_a_prep(home):
    p = prep.packet(prep.due()[0], jobs=[], recs={})
    assert "(not stored: work from the title and the company)" in prep.prompt(p)
    assert p["sponsorship"] == "The posting reads unknown. The employer default is unknown."


def test_numbers_that_are_not_on_the_resume_are_taken_out_and_named(home):
    item = prep.due()[0]
    prep.store_answer(item, answer(), "test", prep.packet(item, jobs=[], recs={}))
    rec = prep.load()["Contoso|R1"]
    assert rec["prep"]["stories"][0]["result"] == "Used by 2,000 people and cut handling time by [?]%."
    assert rec["prep"]["role"] == "A data science role on a [?] person team."
    assert rec["notes"] == [
        "9 in role is not in the posting or your resume, so it was taken out.",
        "40 in stories.1.result is not in the posting or your resume, so it was taken out.",
    ]


def test_too_few_questions_or_no_story_goes_back(home):
    assert prep.check(answer()) == []
    assert prep.check(answer(questions=[], stories=[])) == [
        "questions should hold six to eight questions",
        "stories should hold three stories from the resume",
    ]


def test_the_report_lists_preps_newest_first_with_the_current_status(home):
    for item in prep.due():
        prep.store_answer(item, answer(), "test", prep.packet(item, jobs=[], recs={}))
    applications.set_status("Contoso", "R1", "offer")
    r = prep.report()
    assert {x["key"]: x["status"] for x in r["items"]} == {"Contoso|R1": "offer", "Adatum|R3": "screen"}
    assert r["due"] == 0


def test_numbers_match_with_or_without_thousands_separators():
    assert facts.numbers("2,000 users in 2024, 1.5x faster") == {"2000", "2024", "1.5"}
    clean, notes = facts.lock({"a": ["2000 users", "3 teams"]}, ["2,000 users"])
    assert clean == {"a": ["2000 users", "[?] teams"]} and notes == [
        "3 in a.2 is not in the posting or your resume, so it was taken out."
    ]
