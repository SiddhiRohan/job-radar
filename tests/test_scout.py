"""The company scout: leads from where the person applied, the sponsor lists and the model, each checked with the
request the poll would make; nothing joins companies.json until they follow it. Offline: the careers sites are
stand-ins."""

import json
from pathlib import Path

import pytest

from radar import agentchat, agents, applications, leads, scout, scoutprobe

CFG = {"search_terms": ["data scientist"], "title_patterns": ["data scien", "machine learning"], "agents": {}}
BOARDS = {
    ("greenhouse", "northwind"): [{"title": "Data Scientist"}, {"title": "Recruiter"}],
    ("ashby", "fabrikam-labs"): [{"title": "Machine Learning Engineer"}, {"title": "Data Scientist II"}],
}


def fake_fetch(company, now=None):
    postings = BOARDS.get((company["ats"], company["board"]))
    if postings is None:
        raise ValueError("no such board")
    return [p | {"req_id": str(i)} for i, p in enumerate(postings)]


@pytest.fixture
def home(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    Path("companies").mkdir()
    Path("companies/recheck_later.json").write_text(json.dumps({"Fabrikam Labs": {}}), encoding="utf-8")
    Path("companies/not_on_workday.json").write_text(json.dumps({"Litware": {}}), encoding="utf-8")
    Path("companies.json").write_text(json.dumps([{"name": "Contoso", "tier": 1}]), encoding="utf-8")
    monkeypatch.setattr(scout.expand, "H1B_TOP", {"Adatum", "Contoso", "Booz Allen"})
    monkeypatch.setattr(scoutprobe.boards, "fetch", fake_fetch)
    monkeypatch.setattr(scoutprobe.wd, "count", lambda tenant, shard, site: 40)
    monkeypatch.setattr(scoutprobe.wd, "search", lambda *a, **k: [{"title": "Data Scientist"}, {"title": "Nurse"}])
    applications.add("Northwind", "R1", "Data Scientist")
    return tmp_path


def jobs():
    return [{"company": "Northwind", "req_id": "R1", "url": "https://job-boards.greenhouse.io/northwind/jobs/1"}]


def test_leads_come_best_first_and_never_twice_or_for_an_employer_already_followed(home):
    state = scout.gather({"leads": {}}, jobs=jobs())
    got = {n: (v["source"], v["link"]) for n, v in state["leads"].items()}
    assert got == {
        "Northwind": ("you applied there", "https://job-boards.greenhouse.io/northwind/jobs/1"),
        "Adatum": ("top H-1B sponsor", ""),  # Booz Allen is on the no-sponsorship list; Contoso is followed
        "Fabrikam Labs": ("earlier search", ""),
        "Litware": ("earlier search", ""),
    }
    assert scout.gather(state, jobs=jobs()) == state


def test_a_link_is_checked_there_and_a_name_on_the_boards_a_few_a_run(home, monkeypatch):
    monkeypatch.setattr(scout.store, "load", jobs)
    assert scout.check(CFG, limit=2) == ["Northwind"]  # the linked lead, then the sponsor list, then earlier searches
    now = scout.load()["leads"]
    assert (now["Northwind"]["ats"], now["Northwind"]["roles"], now["Northwind"]["matching"]) == ("greenhouse", 2, 1)
    assert (now["Adatum"]["status"], now["Fabrikam Labs"]["status"]) == ("none", "new")  # the rest wait a run
    assert scout.check(CFG, limit=5) == ["Fabrikam Labs"]
    now = scout.load()["leads"]
    assert (now["Fabrikam Labs"]["ats"], now["Fabrikam Labs"]["url"]) == (
        "ashby",
        "https://jobs.ashbyhq.com/fabrikam-labs",
    )
    assert now["Litware"]["status"] == "none"


def test_a_workday_link_counts_its_roles_and_the_matching_titles(home, monkeypatch):
    site = scoutprobe.at_link("https://contoso.wd5.myworkdayjobs.com/en-US/External/job/X_R1", CFG)
    assert site == ("workday", "https://contoso.wd5.myworkdayjobs.com/External", 40, 1)
    with pytest.raises(ValueError):
        scoutprobe.at_link("https://careers.example.com/jobs", CFG)
    monkeypatch.setattr(scoutprobe.wd, "count", lambda tenant, shard, site: 0)
    with pytest.raises(ValueError, match="no open roles"):  # a site with nothing open is not a find
        scoutprobe.at_link("https://contoso.wd5.myworkdayjobs.com/External", CFG)


def test_a_wrong_or_empty_link_sends_the_scout_to_the_boards_by_name(home, monkeypatch):
    monkeypatch.setitem(BOARDS, ("lever", "tailspin"), [])  # a board with nothing open
    monkeypatch.setattr(scout.store, "load", lambda: [])
    state = scout.gather({"leads": {}})
    state["leads"]["Fabrikam Labs"]["link"] = "https://jobs.lever.co/fabrikam"  # no such board: it is on Ashby
    state["leads"]["Tailspin"] = {"source": "suggested", "link": "https://jobs.lever.co/tailspin", "status": "new"}
    scout.store.write_json(scout.STATE, state)
    assert scout.check(CFG, limit=2) == ["Fabrikam Labs"]
    now = scout.load()["leads"]
    assert (
        now["Fabrikam Labs"]["url"] == "https://jobs.ashbyhq.com/fabrikam-labs" and "note" not in now["Fabrikam Labs"]
    )
    assert (now["Tailspin"]["status"], now["Tailspin"]["note"]) == ("none", "no open roles there")


def test_following_adds_the_employer_and_skipping_only_hides_it(home, monkeypatch):
    monkeypatch.setattr(scout.store, "load", jobs)
    scout.check(CFG, limit=4)
    calls = []
    monkeypatch.setattr(
        scout.add, "add", lambda name, url: calls.append((name, url)) or {"ok": True, "message": "added"}
    )
    assert scout.decide("Northwind", "follow") == {"ok": True, "message": "added"}
    assert calls == [("Northwind", "https://job-boards.greenhouse.io/northwind")]
    assert scout.decide("Fabrikam Labs", "skip")["ok"] and scout.decide("Nobody", "follow")["ok"] is False
    assert {n: v["status"] for n, v in scout.load()["leads"].items() if v["status"] in ("followed", "skipped")} == {
        "Northwind": "followed",
        "Fabrikam Labs": "skipped",
    }


def test_the_report_leads_with_the_most_matching_titles(home, monkeypatch):
    monkeypatch.setattr(scout.store, "load", jobs)
    scout.check(CFG, limit=4)
    r = scout.report()
    assert [f["name"] for f in r["found"]] == ["Fabrikam Labs", "Northwind"] and r["counts"] == {"found": 2, "none": 2}
    assert scout.summary(r)[0].startswith("Fabrikam Labs: ashby, 2 open, 2 matching your titles")
    assert agentchat.call("company_scout", {})["lines"] == scout.summary(r)


def test_the_weekly_leads_add_links_and_new_employers_but_never_followed_ones(home):
    p = leads.packet(leads.due(CFG)[0])
    assert p["check"] == ["Northwind", "Adatum", "Fabrikam Labs", "Litware"] and p["followed"] == ["Contoso"]
    assert "CHECK:\nNorthwind\nAdatum\nFabrikam Labs\nLitware" in leads.prompt(p)  # no stored link for Northwind
    answer = {
        "known": [
            {"name": "Adatum", "link": "https://adatum.wd1.myworkdayjobs.com/Careers"},
            {"name": "Litware", "link": ""},
        ],
        "new": [
            {"name": "Contoso", "link": "", "why": "Already followed."},
            {"name": "Tailspin", "link": "", "why": "Hires ML."},
        ],
    }
    leads.store_answer(leads.due(CFG)[0], answer, "m", p)
    state = scout.load()
    assert state["leads"]["Adatum"]["link"].startswith("https://adatum.wd1") and state["leads"]["Litware"]["link"] == ""
    assert state["leads"]["Tailspin"]["source"] == "suggested" and "Contoso" not in state["leads"]
    assert leads.due(CFG) == [] and len(leads.due(CFG, every=True)) == 1  # weekly, or now when asked


def test_the_runner_writes_the_leads_with_the_model(home, monkeypatch):
    monkeypatch.setattr(agents.score, "load_api_key", lambda required=True: "k")
    answer = {"known": [], "new": [{"name": "Tailspin", "link": "", "why": "Hires ML."}]}
    monkeypatch.setattr(agents.llm, "complete", lambda system, user, schema, max_tokens=0: (answer, "m"))
    assert agents.run(["scout"])["scout"]["made"][0].startswith("leads|")
    assert scout.load()["leads"]["Tailspin"]["why"] == "Hires ML."


def test_a_careers_page_the_poll_cannot_read_is_no_link_and_the_boards_are_tried(home, monkeypatch):
    p = leads.packet(leads.due(CFG)[0])
    answer = {
        "known": [{"name": "Adatum", "link": "https://careers.adatum.example/jobs"}],
        "new": [{"name": "Fabrikam", "link": "https://fabrikam.example/careers", "why": "Hires ML."}],
    }
    leads.store_answer(leads.due(CFG)[0], answer, "m", p)
    state = scout.load()
    assert state["leads"]["Adatum"]["link"] == "" and state["leads"]["Fabrikam"]["link"] == ""
    state["leads"]["Northwind"]["link"] = "https://northwind.example/careers"  # an unreadable link, stored earlier
    scout.store.write_json(scout.STATE, state)
    monkeypatch.setattr(scout.store, "load", lambda: [])
    assert "Northwind" in scout.check(CFG, limit=10)  # found on its board by name instead
