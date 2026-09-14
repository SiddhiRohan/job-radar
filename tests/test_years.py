"""Years-of-experience parsing used by the 6+ years gate."""

import pytest

import filters

CASES = [
    ("3+ years of experience in data engineering", 3),
    ("3-5 years experience with Python", 3),
    ("minimum of 6 years of professional experience", 6),
    ("Bachelor's and 6+ years of relevant experience, or Master's and 4+ years of experience", 4),
    ("At least 7 yrs of hands-on industry experience", 7),
    ("0-2 years of experience", 0),
    ("2 years with Python", None),  # not tied to the word experience
    ("We have been in business for 10 years", None),
    ("Great benefits and a friendly team", None),
]


@pytest.mark.parametrize("text,expected", CASES)
def test_years_required(text, expected):
    assert filters.years_required(text) == expected


def test_gate_threshold_is_six():
    assert filters.years_required("6+ years of experience") >= 6
    assert filters.years_required("5+ years of experience") < 6
