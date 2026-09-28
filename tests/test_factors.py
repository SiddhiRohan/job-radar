"""Sponsorship, location and pay factors are read by rule from the stored posting; the drawer gets seven rows for a
new verdict and none for one stored before factors existed."""

import pytest

from radar import digest, factors, fit, score


def job(verdict=None, **kw):
    j = {
        "company": "GM",
        "req_id": "R1",
        "title": "Data Engineer",
        "location": "Austin, TX",
        "posted_on": "Posted Today",
        "url": "https://x",
        "sponsorship": "likely",
        "sponsorship_evidence": None,
        "description": "",
        **kw,
    }
    if verdict is not None:
        j["verdict"] = verdict
    return j


def new_verdict(**kw):
    four = [
        {"factor": n, "verdict": "meets", "posting": "ask", "resume": "proof", "note": ""} for n in fit.MODEL_FACTORS
    ]
    return {"factors": four, "score_entry": 4, "score_experienced": 4, "sponsorship": "unknown", **kw}


@pytest.mark.parametrize(
    "tag,model,evidence,verdict,note",
    [
        ("yes", "yes", "We will sponsor H-1B visas for this role", "meets", "says it sponsors"),
        ("likely", "unknown", None, "meets", "company default is yes"),
        ("unknown", "unknown", None, "partial", "Neither"),
        ("unlikely", "unknown", None, "gap", "company default is no"),
        ("unlikely", "yes", None, "meets", "model read the posting as sponsoring"),  # Capital One
        ("likely", "no", None, "gap", "model read the posting as not sponsoring"),
        ("no", "no", "Visa sponsorship is not available for this position.", "gap", "rules out sponsorship"),
        ("perm_ad", "unknown", "Salary: $128,731.21 per year", "gap", "PERM"),
    ],
)
def test_sponsorship_factor(tag, model, evidence, verdict, note):
    f = factors.sponsorship(job(new_verdict(sponsorship=model), sponsorship=tag, sponsorship_evidence=evidence))
    assert f["verdict"] == verdict and note in f["note"] and f["rule"] is True
    assert f["posting"] == (evidence or "Not stated") and f["resume"] == ""


def test_sponsorship_shows_the_models_phrase_when_the_regex_found_none():
    j = job(new_verdict(sponsorship="yes", sponsorship_evidence="open to sponsoring visas"), sponsorship="unknown")
    assert factors.sponsorship(j)["posting"] == "open to sponsoring visas"


@pytest.mark.parametrize("tag", ["yes", "likely", "unknown", "unlikely", "no", "perm_ad"])
@pytest.mark.parametrize("model", ["yes", "no", "unknown", None])
def test_sponsorship_badge_agrees_with_the_section(tag, model):
    j = job(new_verdict(sponsorship=model), sponsorship=tag)
    s, badge = digest.sections([j]), factors.sponsorship(j)["verdict"]
    assert (badge == "gap") == bool(s["skipped"]) and (badge == "meets") == bool(s["apply"])


@pytest.mark.parametrize(
    "kw,verdict,note",
    [
        ({"location": "US - Remote"}, "meets", "Remote"),
        ({"detail_location": "Austin, Texas", "additional_locations": ["Remote - USA"]}, "meets", "Remote"),
        ({"description": "This role is fully remote."}, "meets", "Remote"),
        ({"description": "This position is not remote-eligible."}, "meets", "No remote or hybrid"),
        ({"description": "Experience with remote sensing data."}, "meets", "No remote or hybrid"),
        ({"location": "Hybrid - Chicago, IL"}, "meets", "Hybrid"),
        ({"description": "We offer a hybrid work schedule."}, "meets", "Hybrid"),
        ({"description": "Migrate workloads to a hybrid cloud."}, "meets", "No remote or hybrid"),
        ({"location": "Toronto, ON", "non_us": True}, "gap", "Outside the US"),
        ({"location": ""}, "partial", "no location"),
    ],
)
def test_location_factor(kw, verdict, note):
    f = factors.location(job(new_verdict(), **kw))
    assert f["verdict"] == verdict and note in f["note"]


def test_location_names_the_primary_place_and_counts_the_rest():
    j = job(new_verdict(), location="3 Locations", detail_location="Austin, Texas", additional_locations=["A", "B"])
    assert factors.location(j)["posting"] == "Austin, Texas (+2 more)"


def test_pay_factor():
    listed = factors.pay(job(description="The base salary range is $120,000 - $150,000 per year."))
    assert (listed["verdict"], listed["posting"], listed["note"]) == (
        "meets",
        "$120k to $150k",
        "Stated in the posting.",
    )
    missing = factors.pay(job(description="Competitive pay and a 401(k) match."))
    assert (missing["verdict"], missing["posting"]) == ("partial", "Not listed")
    text = "Austin: salary range $90,000 - $120,000.\nSan Jose: salary range $110,000 - $150,000."
    assert "Varies by location" in factors.pay(job(description=text))["note"]


def test_long_evidence_is_clipped_to_twenty_words():
    said = " ".join(f"w{i}" for i in range(30))
    f = factors.sponsorship(job(new_verdict(), sponsorship="no", sponsorship_evidence=said))
    assert f["posting"] == " ".join(f"w{i}" for i in range(20)) + " …"


def test_new_verdict_gives_seven_rows_in_order():
    rows = factors.table(job(new_verdict()))
    assert [r["factor"] for r in rows] == ["experience", "level", "skills", "domain", "sponsorship", "location", "pay"]
    assert [r["rule"] for r in rows] == [False] * 4 + [True] * 3
    assert all(set(r) == {"factor", "verdict", "posting", "resume", "note", "rule"} for r in rows)


def test_old_verdicts_errors_and_unscored_postings_show_nothing_extra():
    old = {"score_entry": 4, "score_experienced": 3, "why": "scored before factors existed"}
    assert factors.table(job(old)) == []
    assert factors.table(job({"error": "API 529: overloaded"})) == []
    assert factors.table(job()) == []
    assert factors.table(dict(job(), verdict=None)) == []


def test_rule_verdicts_carry_an_empty_list_and_show_the_three_rule_rows():
    j = job(years_gate=True, years_required=8)
    j["verdict"] = score.rule_verdict(j)
    assert j["verdict"]["factors"] == []
    assert [r["factor"] for r in factors.table(j)] == ["sponsorship", "location", "pay"]
