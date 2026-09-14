"""Sponsorship phrase matching: the strings that mis-tagged postings this weekend, plus safe ones."""

import pytest

import sponsor

SHOULD_MATCH_NO = [
    "Visa Sponsorship is not available for this position.",  # Caterpillar, missed on 2026-09-13
    "Visa sponsorship is NOT available with this position",
    "At this time, Capital One will not sponsor a new applicant for employment authorization",
    "Ability to obtain a Secret clearance",
    "Must have TS/SCI with polygraph",
    "Must not require sponsorship now or in the future",
    "candidate must be a U.S. citizen",
    "not able to sponsor",
    "unable to sponsor",
    "cannot sponsor",
    "without sponsorship",
    "sponsorship is not offered",
    "no visa sponsorship",
    "subject to EAR restrictions",
]
SHOULD_NOT_MATCH_NO = [
    "Equal opportunity employer",
    "inner ear research",
    "Salary $150,000.00 - $180,000.00",
    "We will sponsor H-1B visas for this role",
    "H1B transfer welcome",
]


@pytest.mark.parametrize("text", SHOULD_MATCH_NO)
def test_no_phrases_match(text):
    assert sponsor.classify(text)[0] == "no", text


@pytest.mark.parametrize("text", SHOULD_NOT_MATCH_NO)
def test_safe_phrases_do_not_match_no(text):
    assert sponsor.classify(text)[0] != "no", text


def test_yes_and_perm_ad():
    assert sponsor.classify("We will sponsor H-1B visas for this role")[0] == "yes"
    assert sponsor.classify("Salary: $128,731.21 per year")[0] == "perm_ad"
    assert sponsor.classify("Send your resume by mail to HR, refer to job code 123")[0] == "perm_ad"


def test_company_default_only_fills_unknown():
    assert sponsor.resolve("unknown", True) == "likely"
    assert sponsor.resolve("unknown", False) == "unlikely"
    assert sponsor.resolve("unknown", None) == "unknown"
    assert sponsor.resolve("no", True) == "no"
