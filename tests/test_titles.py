"""Title rule: the title must name a target role; entry wording widens it; override never rescues a director."""

import json

import pytest

from radar import filters

CFG = json.load(open("config.json", encoding="utf-8"))

KEEP = [
    "Data Engineer - Data Software Engineering and Cloud Platforms, Early Career",
    "Junior Data Scientist",
    "Senior Machine Learning Engineer, Analytics Center of Excellence",
    "Associate Engineer, Agentic AI",
    "Software Engineer I- Enterprise AI Products",
    "Software Engineer, New College Grad, Bellevue - 2027",  # entry wording widens to software engineer
    "Forward Deployed AI Engineer III",
    "(USA) Senior, Data Analyst",
]
DROP = [
    "Machine Operator I - 3rd or Weekend Shift Available",  # one loose word of "machine learning"
    "Clinical Laboratory Scientist I",
    "Mechanical Engineer I (Onsite)",
    "Senior Software Engineer - Underwriting Engineering (Hybrid)",  # software engineer without entry wording
    "Associate Packaging Engineer",
]


@pytest.mark.parametrize("title", KEEP)
def test_kept(title):
    assert filters.title_matches_term(title, None, CFG)


@pytest.mark.parametrize("title", DROP)
def test_dropped(title):
    assert not filters.title_matches_term(title, None, CFG)


@pytest.mark.parametrize(
    "title",
    [
        "Associate Director - AI development",
        "Head, LOB Analytics and Insights (US)",
        "Associate Vice President, Interoperability Engineering",
        "2027 Technology Summer Internship - Early Careers (Software Engineering)",
    ],
)
def test_override_never_rescues_senior_or_intern(title):
    assert filters.title_exclusion(title, CFG) == "seniority"


def test_entry_title():
    assert filters.is_entry_title("Software Engineer 1")
    assert filters.is_entry_title("AI Workflow Specialist Graduate")
    assert not filters.is_entry_title("Senior Data Engineer")
    assert not filters.is_entry_title("Associate Director - AI development")
