"""Board employers in the poll: the Workday path's title, window and US rules, one request per board, and enrichment
from the detail the board already sent."""

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import requests

from radar import boardparse, boards, poll, wd

FIXTURES = Path(__file__).parent / "fixtures"
NOW = datetime(2026, 9, 27, 12, 0, tzinfo=timezone.utc)
CFG = {
    "search_terms": ["data engineer", "data scientist"],
    "entry_terms": ["new college grad"],
    "max_days_ago": 1,
    "entry_max_days_ago": 14,
    "us_only": True,
    "title_must_match_term": True,
    "title_patterns": ["data engineer", "data scien", "machine learning"],
    "entry_title_patterns": ["software (engineer|developer)"],
    "exclude_seniority": ["staff"],
    "exclude_domain": [],
    "include_override": [],
}
US, LONDON = [("New York, NY", None)], [("London, United Kingdom", None)]


def job(p_id, title, days, places=US, text="Build pipelines."):
    return boardparse.posting("Acme", "greenhouse", NOW, p_id, title, NOW - timedelta(days=days), "u", places, text)


def removed_sets():
    return {r: set() for r in poll.RULES}


def test_screen_applies_title_window_and_us_rules():
    jobs = [
        job(1, "Data Scientist", 0),
        job(2, "Staff Data Engineer", 0),
        job(3, "Data Engineer", 0, LONDON),
        job(4, "Data Engineer", 5),  # outside the one-day window and no entry wording
        job(5, "Software Engineer, New College Grad", 9),  # entry wording: the 14-day window and entry patterns
        job(6, "Recruiter", 0),  # no target role in the title
        job(7, "Data Engineer", 0, [("London, United Kingdom", None), ("Austin, TX", None)]),
        job(1, "Data Scientist", 0),  # the same posting twice is kept once
    ]
    found, removed = {}, removed_sets()
    fresh = boards.screen(CFG, {"name": "Acme", "tier": 2}, jobs, 1, found, removed)
    assert set(found) == {"Acme|1", "Acme|5", "Acme|7"} and fresh == 6
    assert (found["Acme|1"]["search_term"], found["Acme|5"]["search_term"]) == ("data scientist", "new college grad")
    assert removed["seniority"] == {"Acme|2"} and removed["non_us"] == {"Acme|3"}
    found3, removed3 = {}, removed_sets()
    boards.screen(CFG, {"name": "Acme", "tier": 3}, jobs, 1, found3, removed3)
    assert "Acme|5" not in found3  # tier 3 gets no entry terms, as on Workday


def test_search_all_reads_each_board_once_and_keeps_polling_after_a_failure(monkeypatch):
    fixture = json.loads((FIXTURES / "greenhouse.json").read_text(encoding="utf-8"))
    calls = []

    def request_json(url, body=None):
        calls.append(url)
        if "lever" in url:
            raise requests.HTTPError("404 Client Error: Not Found")
        return fixture

    searched = []
    monkeypatch.setattr(wd, "request_json", request_json)
    monkeypatch.setattr(wd, "search", lambda *a, **k: searched.append(a[3]) or [])
    companies = [
        {"name": "Gone", "ats": "lever", "board": "gone", "tier": 1},
        {"name": "Acme", "ats": "greenhouse", "board": "acme", "tier": 1},
        {"name": "Adobe", "tenant": "adobe", "shard": "wd5", "site": "ext", "tier": 1},
    ]
    removed = removed_sets()
    found, errors = poll.search_all(CFG, companies, 100000, removed)  # a window wide enough for the fixture dates
    assert len(calls) == 2 and searched == ["data engineer", "data scientist", "new college grad"]
    assert list(found) == ["Acme|8805001002"] and removed["non_us"] == {"Acme|8805002002"}
    assert "Gone" in errors and "404" in errors["Gone"]


def test_enrich_derives_everything_from_the_board_without_a_request(monkeypatch):
    monkeypatch.setattr(wd, "fetch_detail", lambda *a: pytest.fail("a board posting must not fetch a detail"))
    text = "Requires 7+ years of experience with Spark. This is a 12-month contract position. Unable to sponsor visas."
    j = job(9, "Data Engineer", 0, [("London, United Kingdom", "GB"), ("New York, NY", None)], text)
    j["detail"].update(country="GB", country_code="GB")
    poll.enrich(j, {"name": "Acme", "sponsors_h1b": True}, CFG, j.pop("detail"))
    assert j["detail_location"] == "London, United Kingdom; New York, NY" and j["country_code"] == "GB"
    assert j["additional_locations"] == ["New York, NY"] and j["non_us"] is False  # New York keeps it
    assert (j["years_required"], j["years_gate"]) == (7, True)
    assert j["sponsorship"] == "no" and "sponsor" in j["sponsorship_evidence"] and j["contract"] is True
    ashby = boardparse.ashby("Acme", json.loads((FIXTURES / "ashby.json").read_text(encoding="utf-8")), NOW)[0]
    poll.enrich(ashby, {"name": "Acme", "sponsors_h1b": None}, CFG, ashby.pop("detail"))
    assert (ashby["sponsorship"], ashby["contract"], ashby["country"]) == ("yes", False, "United Kingdom")


def test_poll_run_stores_board_postings_without_their_detail(tmp_path, monkeypatch):
    fixture = json.loads((FIXTURES / "greenhouse.json").read_text(encoding="utf-8"))
    monkeypatch.chdir(tmp_path)
    (tmp_path / "config.json").write_text(json.dumps(CFG), encoding="utf-8")
    company = {"name": "Acme", "ats": "greenhouse", "board": "acme", "tier": 1, "verified": True, "sponsors_h1b": True}
    (tmp_path / "companies.json").write_text(json.dumps([company]), encoding="utf-8")
    monkeypatch.setattr(wd, "request_json", lambda url, body=None: fixture)
    monkeypatch.setattr(wd, "fetch_detail", lambda *a: pytest.fail("a board posting must not fetch a detail"))
    monkeypatch.setattr(sys, "argv", ["poll", "--days", "100000"])
    poll.main()
    rows = [json.loads(line) for line in (tmp_path / "jobs.jsonl").read_text(encoding="utf-8").splitlines()]
    assert [r["req_id"] for r in rows] == ["8805001002"] and "detail" not in rows[0]
    row = rows[0]
    assert (row["ats"], row["search_term"], row["sponsorship"]) == ("greenhouse", "data engineer", "likely")
    assert "Spark & SQL" in row["description"] and row["posted_on"].startswith("Posted")
    run = json.loads((tmp_path / "last_run.json").read_text(encoding="utf-8"))
    assert run["removed"]["non_us"] == 1 and run["errors"] == {}
