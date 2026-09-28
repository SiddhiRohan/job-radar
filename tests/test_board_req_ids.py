"""A Greenhouse posting is stored under the board's number, but the employer's emails quote its own requisition id;
the board gives that id too, and an email quoting it moves the application like a Workday id does."""

import json
from pathlib import Path

from radar import applications, boardparse, mail, mailmatch

FIXTURE = Path(__file__).parent / "fixtures" / "greenhouse.json"


def test_greenhouse_postings_keep_the_employers_requisition_id():
    first, second = boardparse.greenhouse("Example", json.loads(FIXTURE.read_text(encoding="utf-8")))
    assert first["req_id"] == "8805001002" and first["requisition_id"] == "R-10042"
    assert "requisition_id" not in second  # the board gave none


def test_an_email_quoting_the_other_id_matches():
    apps = [{"company": "Contoso", "req_id": "8805001002", "title": "Data Engineer", "status": "applied"}]
    jobs = [{"company": "Contoso", "req_id": "8805001002", "requisition_id": "R-10042"}]
    both = mailmatch.with_board_ids(apps, jobs)
    assert mailmatch.by_req_id("Update on your application for R10042", both) == both
    assert mailmatch.by_req_id("Update on your application for R10042", apps) == []


def test_mail_sync_moves_a_board_application_by_its_requisition_id(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(applications, "PATH", tmp_path / "applications.md")
    monkeypatch.setattr(mail, "STATE", tmp_path / "mail.json")
    (tmp_path / "companies.json").write_text(json.dumps([{"name": "Contoso", "ats": "greenhouse"}]), encoding="utf-8")
    posting = {"company": "Contoso", "req_id": "8805001002", "requisition_id": "R-10042", "title": "Data Engineer"}
    (tmp_path / "jobs.jsonl").write_text(json.dumps(posting) + "\n", encoding="utf-8")
    app = {"date": "2026-09-20 10:00", "company": "Contoso", "title": "Data Engineer", "status": "applied"}
    applications.write([app | {"folder": "", "req_id": "8805001002"}])
    message = {"message_id": "<a@x>", "sender": "no-reply@us.greenhouse-mail.io", "subject": "Interview"}
    message |= {"date": "2026-09-24 09:00", "body": "We would like to interview you for R-10042, Data Engineer."}
    assert mail.sync([message])["updated"] == 1
    assert applications.rows()[0]["status"] == "interview"


def test_a_board_id_still_matches_after_another_email_moved_a_status(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(applications, "PATH", tmp_path / "applications.md")
    monkeypatch.setattr(mail, "STATE", tmp_path / "mail.json")
    companies = [{"name": "Contoso", "ats": "greenhouse"}, {"name": "Northwind", "tenant": "northwind"}]
    (tmp_path / "companies.json").write_text(json.dumps(companies), encoding="utf-8")
    posting = {"company": "Contoso", "req_id": "8805001002", "requisition_id": "R-10042", "title": "Data Engineer"}
    (tmp_path / "jobs.jsonl").write_text(json.dumps(posting) + "\n", encoding="utf-8")
    row = {"date": "2026-09-20 10:00", "title": "Data Engineer", "status": "applied", "folder": ""}
    applications.write(
        [row | {"company": "Northwind", "req_id": "R77777"}, row | {"company": "Contoso", "req_id": "8805001002"}]
    )
    first = {
        "message_id": "<1@x>",
        "sender": "northwind@myworkday.com",
        "subject": "Interview",
        "date": "2026-09-24 08:00",
    }
    first["body"] = "We would like to interview you for R77777."
    second = {"message_id": "<2@x>", "sender": "no-reply@us.greenhouse-mail.io", "subject": "Interview"}
    second |= {"date": "2026-09-24 09:00", "body": "We would like to interview you for R-10042, Data Engineer."}
    assert mail.sync([first, second])["updated"] == 2
