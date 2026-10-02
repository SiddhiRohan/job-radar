"""The sponsor map groups employers by what their own postings say and flags defaults their postings contradict."""

from datetime import datetime

from radar import sponsormap

TODAY = datetime(2026, 10, 1)


def posting(company, tag="likely", model="likely", seen="2026-09-28"):
    return {"company": company, "sponsorship": tag, "verdict": {"sponsorship": model}, "first_seen": seen}


def rec(default):
    return {"default": default, "source": "a fictional filing count", "filings": None}


def test_a_no_in_the_wording_or_the_models_read_beats_a_yes():
    assert sponsormap.reading(posting("Contoso", tag="yes", model="no")) == "no"
    assert sponsormap.reading(posting("Contoso", tag="perm_ad", model="yes")) == "no"
    assert sponsormap.reading(posting("Contoso", tag="likely", model="yes")) == "yes"
    assert sponsormap.reading(posting("Contoso")) == "silent"  # a default alone is not the posting saying anything


def test_employers_are_grouped_by_what_their_postings_say():
    jobs = (
        [posting("Contoso", tag="yes"), posting("Contoso")]
        + [posting("Northwind", tag="yes"), posting("Northwind", tag="no")]
        + [posting("Fabrikam", tag="no")] * 2
        + [posting("Fabrikam")]
        + [posting("Adatum")]
    )
    recs = {"Contoso": rec(True), "Northwind": rec(True), "Fabrikam": rec(None), "Adatum": rec(False)}
    r = sponsormap.analyse(jobs, recs, today=TODAY)
    status = {e["company"]: e["status"] for e in r["employers"]}
    assert status == {"Contoso": "sponsors", "Northwind": "mixed", "Fabrikam": "rules_out", "Adatum": "silent"}
    assert [e["company"] for e in r["employers"]] == ["Contoso", "Northwind", "Fabrikam", "Adatum"]
    assert r["counts"] == {"sponsors": 1, "mixed": 1, "rules_out": 1, "silent": 1}


def test_postings_older_than_the_window_do_not_count():
    jobs = [posting("Contoso", tag="yes", seen="2026-07-01"), posting("Contoso", tag="no")]
    r = sponsormap.analyse(jobs, {"Contoso": rec(True)}, today=TODAY)
    assert r["since"] == "2026-08-02"
    assert (r["employers"][0]["yes"], r["employers"][0]["no"]) == (0, 1)


def test_a_default_its_own_postings_contradict_is_flagged():
    jobs = [posting("Contoso", tag="no")] * 4 + [posting("Northwind", tag="yes"), posting("Adatum", model="yes")]
    recs = {"Contoso": rec(True), "Northwind": rec(False), "Adatum": rec(None)}
    flags = {e["company"]: e["flag"] for e in sponsormap.analyse(jobs, recs, today=TODAY)["flags"]}
    assert flags["Contoso"] == "Its default says it sponsors, but 4 of its 4 postings rule sponsorship out."
    assert "does not sponsor, but 1 of its postings say it does" in flags["Northwind"]
    assert "no default yet" in flags["Adatum"]


def test_two_noes_are_not_enough_to_doubt_a_sponsor():
    jobs = [posting("Contoso", tag="no")] * 2
    assert sponsormap.analyse(jobs, {"Contoso": rec(True)}, today=TODAY)["flags"] == []


def test_the_summary_leads_with_the_employers_whose_postings_say_yes():
    jobs = [posting("Contoso", tag="yes")] * 3 + [posting("Contoso", tag="no"), posting("Northwind", tag="yes")]
    lines = sponsormap.summary(sponsormap.analyse(jobs, {}, today=TODAY))
    assert lines[0].startswith("Since 2026-08-02, 2 employers posted: 1 say they sponsor, 1 decide per posting")
    assert lines[1] == "Most postings that say they sponsor: Contoso (3 of 4), Northwind (1 of 1)."


def test_records_join_the_default_with_the_filing_check():
    companies = [{"name": "Contoso", "sponsors_h1b": True, "sponsorship_source": "FY2025 filings"}]
    recs = sponsormap.records(companies, {"Contoso": {"fy2025": "120 LCAs"}, "_about": "how this was checked"})
    assert recs == {"Contoso": {"default": True, "source": "FY2025 filings", "filings": "120 LCAs"}}
