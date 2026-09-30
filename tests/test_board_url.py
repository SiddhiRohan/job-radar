"""Board employers: a careers, board or posting URL resolves to {"ats", "board"}, and adding one records it the way
expand.py records Workday employers."""

import json
import sys
from pathlib import Path

import pytest

from companies import board
from radar import wd

CASES = [
    ("https://boards.greenhouse.io/stripe", "greenhouse", "stripe"),
    ("https://boards.greenhouse.io/stripe/jobs/6421234?gh_jid=6421234", "greenhouse", "stripe"),
    ("https://job-boards.greenhouse.io/databricks/jobs/8805655002", "greenhouse", "databricks"),
    ("https://boards.greenhouse.io/embed/job_board?for=twilio", "greenhouse", "twilio"),
    ("https://boards-api.greenhouse.io/v1/boards/dropbox/jobs?content=true", "greenhouse", "dropbox"),
    ("jobs.lever.co/spotify", "lever", "spotify"),
    ("https://jobs.lever.co/palantir/1a2b3c4d-0001-4000-8000-00000000a001/apply", "lever", "palantir"),
    ("https://api.lever.co/v0/postings/palantir?mode=json", "lever", "palantir"),
    ("https://jobs.ashbyhq.com/snowflake", "ashby", "snowflake"),
    ("https://jobs.ashbyhq.com/snowflake/5e6f7a8b-0001-4000-8000-00000000b001/application", "ashby", "snowflake"),
    ("https://api.ashbyhq.com/posting-api/job-board/snowflake?includeCompensation=true", "ashby", "snowflake"),
]
NOT_BOARDS = [
    "https://adobe.wd5.myworkdayjobs.com/en-US/external_experienced/job/San-Jose/Machine-Learning-Engineer_R171719",
    "https://stripe.com/jobs/search",
    "https://boards.greenhouse.io/",
    "https://jobs.eu.lever.co/example",  # Lever's EU host needs another API; not supported
    "",
]


@pytest.mark.parametrize("url,ats,token", CASES)
def test_board_from_url(url, ats, token):
    assert board.board_from_url(url) == {"ats": ats, "board": token}


@pytest.mark.parametrize("url", NOT_BOARDS)
def test_other_urls_are_not_boards(url):
    assert board.board_from_url(url) is None


def test_check_counts_postings_with_one_request(monkeypatch):
    calls = []
    fixture = json.loads((Path(__file__).parent / "fixtures" / "lever.json").read_text(encoding="utf-8"))
    monkeypatch.setattr(wd, "request_json", lambda url, body=None: calls.append(url) or fixture)
    assert board.check("lever", "example") == 3 and calls == ["https://api.lever.co/v0/postings/example?mode=json"]


def test_add_records_sponsorship_and_tier_like_expand(tmp_path):
    path = tmp_path / "companies.json"
    adobe = {"name": "Adobe", "tenant": "adobe", "shard": "wd5", "site": "x", "tier": 1}
    path.write_text(json.dumps([adobe]), encoding="utf-8")
    board.add("Stripe", "greenhouse", "stripe", 500, path)  # on expand.py's H-1B list
    board.add("Dropbox", "greenhouse", "dropbox", 120, path)  # on no list: unknown, tier 2 until checked
    board.add("Stripe", "greenhouse", "stripe", 510, path)  # a second add updates the entry
    rows = json.loads(path.read_text(encoding="utf-8"))
    assert [r["name"] for r in rows] == ["Adobe", "Dropbox", "Stripe"]
    stripe = rows[2]
    assert (stripe["ats"], stripe["board"], stripe["open_roles"]) == ("greenhouse", "stripe", 510)
    assert stripe["verified"] is True and "tenant" not in stripe
    assert (stripe["sponsors_h1b"], stripe["tier"]) == (True, 2) and "H-1B" in stripe["sponsorship_source"]
    assert (rows[1]["sponsors_h1b"], rows[1]["tier"]) == (None, 2)
    with pytest.raises(ValueError):
        board.add("Adobe", "lever", "adobe", 1, path)  # a Workday employer is never switched silently


def test_cli_checks_the_board_then_adds_it(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "companies.json").write_text("[]", encoding="utf-8")
    monkeypatch.setattr(board, "check", lambda ats, token: 42)
    monkeypatch.setattr(sys, "argv", ["board", "Palantir", "https://jobs.lever.co/palantir"])
    board.main()
    [added] = json.loads((tmp_path / "companies.json").read_text(encoding="utf-8"))
    assert (added["name"], added["ats"], added["board"], added["open_roles"]) == ("Palantir", "lever", "palantir", 42)
    assert "42 open postings" in capsys.readouterr().out
