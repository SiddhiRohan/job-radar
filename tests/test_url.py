"""Workday job URL parsing: five real URLs from jobs.jsonl, expected req IDs as Workday reports them."""

import pytest

import wd

CASES = [
    (
        "https://nvidia.wd5.myworkdayjobs.com/en-US/NVIDIAExternalCareerSite/job/US-CA-Santa-Clara/Product-Engineer---Datacenter_JR2023146",
        ("nvidia", "wd5", "NVIDIAExternalCareerSite", "JR2023146"),
    ),
    (
        "https://salesforce.wd12.myworkdayjobs.com/en-US/External_Career_Site/job/Georgia---Atlanta/Senior-Data-Engineer_JR359294-1",
        ("salesforce", "wd12", "External_Career_Site", "JR359294"),
    ),
    (
        "https://adobe.wd5.myworkdayjobs.com/en-US/external_experienced/job/San-Jose/Machine-Learning-Engineer_R171719",
        ("adobe", "wd5", "external_experienced", "R171719"),
    ),
    (
        "https://capitalone.wd12.myworkdayjobs.com/en-US/Capital_One/job/Cambridge-MA/Part-Time-Applied-Data-Scientist_R1000592",
        ("capitalone", "wd12", "Capital_One", "R1000592"),
    ),
    (
        "https://walmart.wd504.myworkdayjobs.com/en-US/WalmartExternal/job/USA-Bentonville-Global-Tech-AR-BENTONVILLE-Home-Office/XMLNAME--USA--Senior--Data-Scientist_R-2628137-1",
        ("walmart", "wd504", "WalmartExternal", "R-2628137"),
    ),
]


@pytest.mark.parametrize("url,expected", CASES)
def test_parse_job_url(url, expected):
    tenant, shard, site, ext, req_id = wd.parse_job_url(url)
    assert (tenant, shard, site, req_id) == expected
    assert ext.startswith("/job/")


def test_apply_suffix_and_missing_locale_are_tolerated():
    t, s, site, ext, req = wd.parse_job_url(
        "https://adobe.wd5.myworkdayjobs.com/external_experienced/job/San-Jose/Machine-Learning-Engineer_R171719/apply/applyManually"
    )
    assert (t, site, req) == ("adobe", "external_experienced", "R171719")
    assert not ext.endswith("/apply/applyManually")


def test_non_workday_url_is_rejected():
    assert wd.parse_job_url("https://jobs.lever.co/spotify/123") is None
