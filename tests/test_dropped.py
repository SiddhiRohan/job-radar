"""The drop log: every posting a title or location rule removed is kept for two weeks, so the filter auditor can
check the rules against what they threw away. Offline."""

from datetime import datetime

import pytest

from radar import boards, dropped, poll
from tests.test_poll_boards import CFG, LONDON, job, removed_sets

DAY = datetime(2026, 10, 7)


@pytest.fixture
def home(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    return tmp_path


def drop(n, title, reason="off_target", company="Contoso"):
    return {"key": f"{company}|R{n}", "company": company, "title": title, "url": "", "location": "", "reason": reason}


def test_a_board_logs_each_drop_with_its_title_and_rule():
    jobs = [job(1, "Data Scientist", 0), job(2, "Staff Data Engineer", 0), job(3, "Data Engineer", 0, LONDON)]
    jobs.append(job(6, "Recruiter", 0))
    log = []
    boards.screen(CFG, {"name": "Acme", "tier": 2}, jobs, 1, {}, removed_sets(), log)
    assert sorted((i["title"], i["reason"]) for i in log) == [
        ("Data Engineer", "non_us"),
        ("Recruiter", "off_target"),
        ("Staff Data Engineer", "seniority"),
    ]
    assert {i["key"] for i in log} == {"Acme|2", "Acme|3", "Acme|6"} and poll.RULES  # the poll counts these as before


def test_the_log_keeps_two_weeks_one_row_per_posting_and_rule(home):
    dropped.record([drop(1, "Recruiter"), drop(2, "Staff Data Engineer", "seniority")], when=datetime(2026, 9, 25))
    dropped.record([drop(1, "Recruiter"), drop(3, "Analyst, Marketing")], when=DAY)
    rows = dropped.load()["items"]
    assert sorted((r["key"], r["day"]) for r in rows) == [
        ("Contoso|R1", "2026-10-07"),
        ("Contoso|R2", "2026-09-25"),
        ("Contoso|R3", "2026-10-07"),
    ]
    dropped.record([], when=datetime(2026, 10, 10))
    assert "Contoso|R2" not in {r["key"] for r in dropped.load()["items"]}  # older than two weeks
    assert dropped.counts("2026-10-01") == {"off_target": 2}


def test_a_sample_stands_for_many_drops_by_title(home):
    rows = [drop(n, "Applied Scientist", company=f"Co{n}") for n in range(4)]
    rows += [
        drop(10, "applied  scientist", company="Co9"),
        drop(11, "Recruiter"),
        drop(12, "Staff Data Scientist", "seniority"),
    ]
    dropped.record(rows, when=DAY)
    got = dropped.sample("2026-10-01", per={"off_target": 1, "seniority": 5})
    assert [(i["title"], i["count"], i["reason"]) for i in got] == [
        ("Applied Scientist", 5, "off_target"),  # case and spacing do not split a title
        ("Staff Data Scientist", 1, "seniority"),
    ]
