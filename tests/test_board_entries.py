"""Code that looks employers up by Workday tenant skips job-board employers, which have none, instead of failing."""

import json

from companies import report_companies
from radar import applications, digest, evaluate, mail

WORKDAY = {"name": "Northwind", "tenant": "northwind", "shard": "wd12", "site": "Northwind_Careers", "tier": 1}
BOARD = {"name": "Contoso", "ats": "greenhouse", "board": "contoso", "tier": 2}


def use_companies(tmp_path, monkeypatch):
    (tmp_path / "companies.json").write_text(json.dumps([WORKDAY, BOARD]), encoding="utf-8")
    monkeypatch.chdir(tmp_path)


def test_mail_sync_maps_tenants_past_board_employers(tmp_path, monkeypatch):
    monkeypatch.setattr(applications, "PATH", tmp_path / "applications.md")
    monkeypatch.setattr(mail, "STATE", tmp_path / "mail.json")
    app = {"date": "2026-09-20 10:00", "company": "Northwind", "title": "AI Engineer 3", "status": "applied"}
    applications.write([app | {"folder": "", "req_id": "R1000001"}])
    use_companies(tmp_path, monkeypatch)
    message = {"message_id": "<a@x>", "sender": "northwind@myworkday.com", "subject": "Interview"}
    message |= {"date": "2026-09-24 09:00", "body": "We would like to interview you for R1000001."}
    assert mail.sync([message])["updated"] == 1


def test_pasted_workday_url_still_finds_its_employer(tmp_path, monkeypatch):
    use_companies(tmp_path, monkeypatch)
    stored = {"company": "Northwind", "req_id": "R1000592", "title": "Applied Data Scientist"}
    monkeypatch.setattr(digest, "load_jsonl", lambda path: [stored])
    url = "https://northwind.wd12.myworkdayjobs.com/en-US/Northwind_Careers/job/Cambridge-MA/Applied-Data-Scientist_R1000592"
    assert evaluate.ingest_url(url) is stored


def test_companies_report_counts_a_board_as_one_request():
    assert report_companies.seconds(BOARD, 5, {2: 3}) == report_companies.SEC_PER_PAGE
    assert report_companies.seconds(WORKDAY, 5, {1: 3}) == 5 * 3 * report_companies.SEC_PER_PAGE
    assert report_companies.where(BOARD) == "greenhouse | contoso"
    assert report_companies.where(WORKDAY) == "northwind.wd12 | Northwind_Careers"
