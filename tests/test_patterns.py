"""Rejection patterns: buckets, support threshold, and honest wording with little data."""

from radar import patterns


def app(company, title, status, req):
    return {
        "date": "2026-09-20 10:00",
        "company": company,
        "title": title,
        "status": status,
        "folder": "",
        "req_id": req,
    }


def job(company, req, entry, exp, years=None, base="experienced", sponsorship="likely"):
    return {
        "company": company,
        "req_id": req,
        "years_required": years,
        "sponsorship": sponsorship,
        "verdict": {"score_entry": entry, "score_experienced": exp, "recommended_resume": base},
    }


APPS = [
    app("A", "Senior Data Engineer", "rejected", "1"),
    app("B", "Senior Data Scientist", "rejected", "2"),
    app("C", "Senior ML Engineer", "rejected", "3"),
    app("D", "Data Engineer II", "applied", "4"),
    app("E", "Associate Data Scientist", "screen", "5"),
    app("F", "Data Analyst", "applied", "6"),
]
JOBS = [
    job("A", "1", 2, 4, 5),
    job("B", "2", 2, 4, 5),
    job("C", "3", 3, 4, 6),
    job("D", "4", 3, 3, 2, "entry"),
    job("E", "5", 4, 3, 1, "entry"),
    job("F", "6", 3, 3),
]


def test_dimensions_bucket_a_posting():
    d = patterns.dimensions(APPS[0], JOBS[0])
    assert d["Title family"] == "Data engineer" and d["Seniority in title"] == "Senior"
    assert d["Fit score"] == "score 4" and d["Years asked"] == "3 to 5" and d["Resume base"] == "experienced"


def test_senior_titles_show_as_the_pattern():
    r = patterns.analyse(APPS, JOBS)
    assert r["total"] == 6 and r["rejected"] == 3 and r["responded"] == 1 and r["enough_data"]
    top = r["findings"][0]
    assert top["dimension"] == "Seniority in title" and top["bucket"] == "Senior"
    assert top["applied"] == 3 and top["rejected"] == 3 and top["rate"] == 1.0


def test_small_buckets_are_not_findings():
    r = patterns.analyse(APPS, JOBS)
    assert all(f["rejected"] >= 3 for f in r["findings"])
    assert not any(f["dimension"] == "Company" for f in r["findings"])  # one application per company


def test_summary_is_honest_with_little_data():
    few = [APPS[0], APPS[3]]
    assert "too few" in patterns.summary(patterns.analyse(few, JOBS))[0]
    lines = patterns.summary(patterns.analyse(APPS, JOBS))
    assert (
        lines[0].startswith("3 of 6 applications were rejected (50%)")
        and "Senior was rejected 3 of 3 times" in lines[1]
    )


def test_missing_posting_still_counts():
    r = patterns.analyse([app("Z", "Data Engineer", "rejected", "9")] * 3, [])
    assert r["tallies"]["Fit score"]["unscored"]["rejected"] == 3


def test_every_application_comes_with_its_buckets():
    r = patterns.analyse(APPS, JOBS)
    assert len(r["apps"]) == 6
    first = r["apps"][0]
    assert (first["company"], first["title"], first["status"]) == ("A", "Senior Data Engineer", "rejected")
    assert first["dims"]["Seniority in title"] == "Senior" and first["dims"]["Company"] == "A"
    senior = [a["company"] for a in r["apps"] if a["dims"]["Seniority in title"] == "Senior"]
    assert senior == ["A", "B", "C"]  # the same three the Senior bucket counts
