"""Follow-up drafts: only quiet applications whose posting is still up, kept until sent, dismissed or moot. Offline."""

import json
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from radar import applications, followup

TODAY = datetime(2026, 10, 1)


@pytest.fixture
def home(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        followup.resumes, "bases", lambda: {"entry": "Entry resume", "experienced": "Built 3 pipelines."}
    )
    applications.write(
        [
            {
                "date": "2026-09-10 09:00",
                "company": "Contoso",
                "title": "Data Engineer",
                "status": "applied",
                "req_id": "R1",
            },
            {
                "date": "2026-09-12 09:00",
                "company": "Northwind",
                "title": "ML Engineer",
                "status": "applied",
                "req_id": "R2",
            },
            {"date": "2026-09-14 09:00", "company": "Adatum", "title": "Analyst", "status": "screen", "req_id": "R3"},
            {
                "date": "2026-09-28 09:00",
                "company": "Fabrikam",
                "title": "Data Scientist",
                "status": "applied",
                "req_id": "R4",
            },
        ]
    )
    return tmp_path


def watched(**status):
    p = Path(".cache/ui/watch.json")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"postings": {k: {"status": v} for k, v in status.items()}}), encoding="utf-8")


def draft(**over):
    d = {
        "linkedin_note": "I applied for the Data Engineer role (R1) and built 3 pipelines like yours.",
        "email_subject": "Data Engineer application, R1",
        "email_body": " ".join(["word"] * 70),
        "search_hint": "Contoso recruiter data",
    }
    return d | over


def test_quiet_applications_with_a_live_posting_are_due_oldest_first(home):
    watched(**{"Northwind|R2": "open"})
    assert [i["company"] for i in followup.due(today=TODAY)] == ["Contoso", "Northwind"]
    watched(**{"Contoso|R1": "closed"})  # a follow-up to a filled role is wasted
    assert [i["company"] for i in followup.due(today=TODAY)] == ["Northwind"]


def test_the_wait_comes_from_config(home):
    cfg = {"agents": {"followup_after_days": 1}}
    assert [i["company"] for i in followup.due(cfg, today=TODAY)] == ["Contoso", "Northwind", "Fabrikam"]


def test_an_application_with_a_draft_is_not_due_again(home):
    item = followup.due(today=TODAY)[0]
    followup.store_answer(item, draft(), "test", followup.packet(item, jobs=[]))
    assert [i["company"] for i in followup.due(today=TODAY)] == ["Northwind"]


def test_a_note_too_long_for_linkedin_or_a_rambling_email_goes_back(home):
    assert followup.check(draft()) == []
    assert followup.check(draft(linkedin_note="x" * 300, email_body="Too short.")) == [
        "linkedin_note is 300 characters; it must stay under 300",
        "email_body is 2 words; write 60 to 110",
    ]


def test_numbers_not_in_the_posting_or_resume_are_taken_out(home):
    item = followup.due(today=TODAY)[0]
    followup.store_answer(item, draft(email_subject="5 reasons to hire me"), "test", followup.packet(item, jobs=[]))
    rec = followup.load()["Contoso|R1"]
    assert rec["draft"]["linkedin_note"].endswith("(R1) and built 3 pipelines like yours.")
    assert rec["draft"]["email_subject"] == "[?] reasons to hire me"
    assert rec["notes"] == ["5 in email_subject is not in the posting or your resume, so it was taken out."]


def test_a_draft_leaves_the_list_when_sent_when_the_application_moves_or_the_posting_closes(home):
    for item in followup.due(cfg={"agents": {"followup_after_days": 1}}, today=TODAY):
        followup.store_answer(item, draft(), "test", followup.packet(item, jobs=[]))
    assert [r["company"] for r in followup.report()["items"]] == ["Contoso", "Northwind", "Fabrikam"]
    assert followup.done("Contoso|R1", "sent") and not followup.done("Contoso|R1", "shouted")
    applications.set_status("Northwind", "R2", "rejected")
    watched(**{"Fabrikam|R4": "closed"})
    assert followup.report()["items"] == []
    assert followup.load()["Contoso|R1"]["done"].startswith("sent ")


def test_the_draft_is_signed_with_the_owners_name(home, monkeypatch):
    monkeypatch.setenv("OWNER_SHORT", "Jane")
    assert "ending with the sign-off Jane." in followup.rules()


def test_the_application_date_is_a_known_number(home):
    item = followup.due(today=TODAY)[0]
    body = "I applied on September 10 and wanted to follow up."
    followup.store_answer(item, draft(email_body=body), "test", followup.packet(item, jobs=[]))
    assert followup.load()["Contoso|R1"]["draft"]["email_body"] == body


def test_one_follow_up_per_employer_at_a_time(home):
    rows = applications.rows() + [
        {"date": "2026-09-11 09:00", "company": "Contoso", "title": "ML Engineer", "status": "applied", "req_id": "R5"}
    ]
    applications.write(rows)
    assert [i["key"] for i in followup.due(today=TODAY)] == ["Contoso|R1", "Northwind|R2"]  # the oldest Contoso role
    followup.store_answer(followup.due(today=TODAY)[0], draft(), "test", followup.packet(followup.due()[0], jobs=[]))
    assert [i["key"] for i in followup.due(today=TODAY)] == ["Northwind|R2"]  # a draft is waiting for Contoso
    followup.done("Contoso|R1", "sent")
    assert [i["key"] for i in followup.due(today=TODAY)] == ["Northwind|R2"]  # sent today: give the recruiter time
    later = datetime.now() + timedelta(days=15)  # drafts are stamped with the real date
    assert "Contoso|R5" in [i["key"] for i in followup.due(today=later)]  # two weeks on, the other role may follow
