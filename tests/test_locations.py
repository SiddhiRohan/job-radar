"""US-only rule on listed places. Greenhouse gives no country, so its places are judged by their words alone; these
are real place strings from live boards on 2026-09-27."""

import pytest

from radar import filters

ABROAD = [
    "Belgrade, Serbia",
    "Ukraine Anywhere",
    "Remote - Estonia",
    "Remote - Cyprus",
    "Ljubljana, Slovenia",
    "Vilnius, Lithuania",
    "British Columbia",
    "Quebec",
    "Frankfurt",
    "São Paulo",
    "EMEA",
    "Remote - Abu Dhabi",
]
HOME_OR_UNCLEAR = [
    "United States - Remote",
    "Remote - US: Select locations",
    "US-Remote",
    "San Francisco, California",
    "Northeast - United States",
    "Austin",
    "Remote",
    "N/A",
]


@pytest.mark.parametrize("place", ABROAD)
def test_places_abroad_are_non_us(place):
    assert filters.looks_non_us(place)


@pytest.mark.parametrize("place", HOME_OR_UNCLEAR)
def test_us_and_unclear_places_are_kept(place):
    assert not filters.looks_non_us(place)
