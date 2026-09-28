"""python -m companies.add: one command for any link to an employer's jobs. Offline: the one check request is
replaced, so these never reach Workday or a job board."""

import json

import pytest

from companies import add, board

SITE = "https://northwind.wd12.myworkdayjobs.com/en-US/Northwind_Careers"
NORTHWIND = ("northwind", "wd12", "Northwind_Careers")


@pytest.mark.parametrize(
    "url, where",
    [
        (SITE, NORTHWIND),
        (SITE + "/job/Austin-TX/Data-Engineer_R1000592", NORTHWIND),
        ("https://Northwind.WD12.myworkdayjobs.com/Northwind_Careers?q=data", NORTHWIND),
        ("https://jobs.lever.co/contoso/1234", None),
        ("https://careers.northwind.example/jobs", None),
    ],
)
def test_workday_addresses_come_from_the_link(url, where):
    assert add.workday_from_url(url) == where


@pytest.fixture
def listing(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    path = tmp_path / "companies.json"
    path.write_text(json.dumps([{"name": "Contoso", "ats": "greenhouse", "board": "contoso", "tier": 2}]), "utf-8")
    return path


def test_a_workday_link_adds_a_verified_employer(listing, monkeypatch, capsys):
    monkeypatch.setattr(add.wd, "count", lambda tenant, shard, site: 42)
    assert add.main(["Northwind", SITE + "/job/Austin-TX/Data-Engineer_R1000592"]) == 0
    entry = next(c for c in json.loads(listing.read_text("utf-8")) if c["name"] == "Northwind")
    assert (entry["tenant"], entry["shard"], entry["site"]) == NORTHWIND and entry["open_roles"] == 42
    assert entry["verified"] and entry["tier"] == 2  # sponsorship unknown: tier 2 until filings are recorded
    assert "42 open postings" in capsys.readouterr().out


def test_a_board_link_goes_through_the_board_path(listing, monkeypatch):
    monkeypatch.setattr(board, "check", lambda ats, name: 7)
    assert add.main(["Fabrikam", "https://jobs.ashbyhq.com/fabrikam/abc-123"]) == 0
    entry = next(c for c in json.loads(listing.read_text("utf-8")) if c["name"] == "Fabrikam")
    assert (entry["ats"], entry["board"], entry["open_roles"]) == ("ashby", "fabrikam", 7)


def test_other_links_and_clashing_systems_are_refused(listing, monkeypatch, capsys):
    before = listing.read_text("utf-8")
    assert add.main(["Northwind", "https://careers.northwind.example/jobs"]) == 1
    monkeypatch.setattr(add.wd, "count", lambda tenant, shard, site: 3)
    assert add.main(["Contoso", SITE]) == 1  # Contoso is a Greenhouse employer already
    assert listing.read_text("utf-8") == before
    assert "greenhouse employer" in capsys.readouterr().out
