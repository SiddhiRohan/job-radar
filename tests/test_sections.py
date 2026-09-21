"""Digest sectioning: junior roles stay visible, and a second run on the same day still reports the day's rows."""

from radar import digest


def job(title, entry, exp, **kw):
    return {
        "company": "GM",
        "req_id": title[:6],
        "title": title,
        "location": "Austin, TX",
        "posted_on": "Posted Today",
        "url": "https://x",
        "sponsorship": kw.pop("sponsorship", "likely"),
        "verdict": {"score_entry": entry, "score_experienced": exp, "apply": False},
        **kw,
    }


def test_entry_role_scoring_three_is_not_buried():
    s = digest.sections([job("ML Systems Engineer, Data Labeling - Early Career", 3, 2)])
    assert len(s["entry"]) == 1 and not s["lower"]


def test_strong_entry_role_still_counts_as_apply():
    s = digest.sections([job("Data Scientist I", 4, 4)])
    assert len(s["apply"]) == 1 and not s["entry"]


def test_weak_entry_role_stays_in_the_tail():
    s = digest.sections([job("Associate SAP Data Analyst", 2, 2)])
    assert len(s["lower"]) == 1 and not s["entry"]


def test_senior_role_scoring_three_stays_in_the_tail():
    s = digest.sections([job("Senior Data Engineer", 3, 3)])
    assert len(s["lower"]) == 1 and not s["entry"]


def test_entry_never_overrides_sponsorship_no():
    s = digest.sections([job("Junior Data Scientist", 3, 3, sponsorship="no")])
    assert len(s["skipped"]) == 1 and not s["entry"]


def with_model(j, read):
    j["verdict"]["sponsorship"] = read
    return j


def test_posting_that_sponsors_beats_a_negative_company_default():
    """Capital One: company default was false, but postings without the no-sponsorship sentence do sponsor."""
    s = digest.sections([with_model(job("Senior AI Engineer", 2, 4, sponsorship="unlikely"), "yes")])
    assert len(s["apply"]) == 1 and not s["skipped"]


def test_negative_company_default_still_skips_without_evidence():
    s = digest.sections([with_model(job("Data Engineer", 4, 4, sponsorship="unlikely"), "unlikely")])
    assert len(s["skipped"]) == 1 and not s["apply"]


def test_model_no_still_wins_over_a_positive_default():
    s = digest.sections([with_model(job("Data Engineer", 4, 4, sponsorship="likely"), "no")])
    assert len(s["skipped"]) == 1 and not s["apply"]


def test_unknown_company_with_a_sponsoring_posting_reaches_apply():
    s = digest.sections([with_model(job("Data Scientist", 4, 4, sponsorship="unknown"), "yes")])
    assert len(s["apply"]) == 1 and not s["maybe"]


def test_sections_cover_every_posting_once():
    rows = [
        job("Data Scientist I", 4, 4),
        job("Junior Data Engineer", 3, 2),
        job("Senior Data Engineer", 3, 3),
        job("Contract Data Engineer", 4, 4, contract=True),
    ]
    s = digest.sections(rows)
    assert sum(len(v) for v in s.values()) == len(rows)


def test_digest_uses_the_run_date_not_the_exact_timestamp():
    """A second run on the same day writes a new ran_at; the day's postings must still appear."""
    rows = [job("Data Scientist I", 4, 4, first_seen="2026-09-19T11:31:02+00:00")]
    day, md = digest.build({"ran_at": "2026-09-19T12:39:59+00:00", "companies_polled": 93}, rows)
    assert day == "2026-09-19"
    assert "New postings kept: 1" in md and "## Apply (1)" in md
