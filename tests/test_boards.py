"""Job boards: Greenhouse, Lever and Ashby JSON read into poll.py's posting shape. Dates, places, pay and text."""

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from radar import boardparse, boards, filters, salary, wd

FIXTURES = Path(__file__).parent / "fixtures"
NOW = datetime(2026, 9, 27, 12, 0, tzinfo=timezone.utc)
KEYS = {"company", "title", "location", "posted_on", "posted_days_ago", "req_id", "url", "ats", "detail"}
DETAIL = {"description", "title", "location", "additional_locations", "country", "country_code", "time_type", "non_us"}


def load(name):
    return json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))


def test_greenhouse_dates_places_and_text():
    first, second = boardparse.greenhouse("Example", load("greenhouse"), NOW)  # the posting without an id is skipped
    assert set(first) == KEYS and set(first["detail"]) == DETAIL
    assert (first["req_id"], first["title"], first["ats"]) == ("8805001002", "Data Engineer, New Grad", "greenhouse")
    assert first["url"] == "https://example.com/careers/job?gh_jid=8805001002"
    assert (first["posted_days_ago"], first["posted_on"]) == (7, "Posted 7 Days Ago")  # first_published, not updated_at
    assert first["location"] == "San Francisco, California; London, United Kingdom"
    assert first["detail"]["additional_locations"] == ["London, United Kingdom"]
    assert first["detail"]["non_us"] is False  # one US place keeps a posting that also lists London
    text = first["detail"]["description"]
    assert "Spark & SQL" in text and "- 2+ years of experience with Python" in text and "&lt;" not in text
    assert salary.extract(text)["text"] == "$120k to $150k" and not text.startswith("Pay range")
    assert (second["posted_on"], second["detail"]["non_us"]) == ("Posted Today", True)  # updated_at stands in


def test_lever_country_code_sections_and_pay():
    first, second, bare = boardparse.lever("Example", load("lever"), NOW)
    assert first["req_id"] == "1a2b3c4d-0001-4000-8000-00000000a001"
    assert (first["title"], first["posted_on"]) == ("Data Scientist", "Posted Yesterday")
    d = first["detail"]
    assert (d["country_code"], d["additional_locations"], d["time_type"]) == ("GB", ["New York, NY"], "Full-time")
    assert d["non_us"] is False and not filters.detail_non_us(d)  # London first, but New York is listed too
    text = d["description"]
    assert text.startswith("Pay range: $130,000 - $170,000 per year\n\n")  # salaryRange, since the text has none
    order = ["A World-Changing Company", "What You'll Do", "- Model demand with Python & SQL.", "Life at Example"]
    assert [text.index(s) for s in order] == sorted(text.index(s) for s in order)
    assert second["detail"]["non_us"] is True and filters.detail_non_us(second["detail"])
    assert not second["detail"]["description"].startswith("Pay range")  # the text states its own range
    assert (bare["posted_days_ago"], bare["posted_on"], bare["location"]) == (999, "", "")  # outside every window
    assert bare["detail"]["non_us"] is False and bare["detail"]["description"] == ""


def test_ashby_country_per_place_compensation_and_unlisted():
    first, second = boardparse.ashby("Example", load("ashby"), NOW)  # the unlisted posting is skipped
    d = first["detail"]
    assert (first["posted_on"], first["location"]) == ("Posted Today", "GB-London; US-NY-New York")
    assert (d["country"], d["country_code"], d["time_type"], d["non_us"]) == ("United Kingdom", None, "FullTime", False)
    assert d["description"].startswith("Pay range: $160K - $230K\n\nShip ranking models.")
    assert salary.extract(d["description"])["text"] == "$160k to $230k"
    assert second["detail"]["non_us"] is True  # "Remote" with a Canadian address
    assert second["detail"]["description"] == "Dashboards & SQL."  # HTML when the plain text is empty
    assert (second["posted_days_ago"], second["posted_on"]) == (26, "Posted 26 Days Ago")


@pytest.mark.parametrize(
    "company,url",
    [
        (
            {"name": "G", "ats": "greenhouse", "board": "g"},
            "https://boards-api.greenhouse.io/v1/boards/g/jobs?content=true",
        ),
        ({"name": "L", "ats": "Lever", "board": "l"}, "https://api.lever.co/v0/postings/l?mode=json"),
        (
            {"name": "A", "ats": "ashby", "board": "a b"},
            "https://api.ashbyhq.com/posting-api/job-board/a%20b?includeCompensation=true",
        ),
    ],
)
def test_fetch_makes_one_request_per_board(monkeypatch, company, url):
    calls = []
    fixture = load(boards.system(company))
    monkeypatch.setattr(wd, "request_json", lambda u, body=None: calls.append(u) or fixture)
    postings = boards.fetch(company, NOW)
    assert calls == [url] and postings and all(p["company"] == company["name"] for p in postings)


def test_workday_entries_are_not_boards_and_bad_entries_raise():
    assert boards.system({"name": "Adobe", "tenant": "adobe"}) is None
    assert boards.system({"name": "X", "ats": "Workday"}) is None
    with pytest.raises(ValueError):
        boards.fetch({"name": "X", "ats": "smartrecruiters", "board": "x"})
    with pytest.raises(ValueError):
        boards.fetch({"name": "X", "ats": "greenhouse"})  # no board token
    with pytest.raises(ValueError):
        boardparse.greenhouse("X", {"status": 404, "error": "Job not found"})
    with pytest.raises(ValueError):
        boardparse.lever("X", {"ok": False, "error": "Document not found"})


@pytest.mark.parametrize(
    "days,text", [(0, "Posted Today"), (1, "Posted Yesterday"), (5, "Posted 5 Days Ago"), (45, "Posted 30+ Days Ago")]
)
def test_posted_on_reads_like_workday(days, text):
    assert boardparse.posted_on(days) == text
    assert wd.parse_days_ago(text) == min(days, 30)


def test_dates_from_iso_and_epoch_milliseconds():
    assert boardparse.days_ago(boardparse.when("2026-09-26T23:30:00-04:00"), NOW) == 0  # 03:30 UTC on the 27th
    assert boardparse.days_ago(boardparse.when("2026-09-25T10:00:00Z"), NOW) == 2
    assert boardparse.days_ago(boardparse.when(1790434800000), NOW) == 1
    assert boardparse.days_ago(boardparse.when("2026-09-30T00:00:00Z"), NOW) == 0  # a clock ahead is not negative
    assert boardparse.when(None) is None and boardparse.when("soon") is None
    assert boardparse.days_ago(None, NOW) == 999 and boardparse.posted_on(999) == ""
