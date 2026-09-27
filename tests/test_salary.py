"""Pay ranges come from description text in many formats; money that is not pay must not be read as a salary."""

import pytest

from radar import salary

CASES = [
    ("Compensation\nNew Jersey Pay Range: $78,505.90 - $117,758.85\n", "$79k to $118k", "year"),
    ("Austin, TX | Salary: $167,149.00-221,500.00 per annum.", "$167k to $222k", "year"),
    ("Summary pay range:\n$80,750-109,250\n", "$81k to $109k", "year"),
    ("Annual Salary\n$105,000.00 - $215,000.00The above annual salary range", "$105k to $215k", "year"),
    ("incentive opportunities.\n\n$118.9K - $172.2K USD\n", "$119k to $172k", "year"),
    ("estimated salary range for this position is $83,100.00 to $ 129,300.00 USD per year", "$83k to $129k", "year"),
    ("The annual base salary range for this position is USD 129,400.00 To USD 207,000.00", "$129k to $207k", "year"),
    ("the base salary for this role if filled within Jersey City, NJ is $110k - $115k/year", "$110k to $115k", "year"),
    ("Base Pay Range: $160,000 USD - $240,000 USD", "$160k to $240k", "year"),
    (
        "The hourly pay range estimated for this position based in Virginia is $21.00–$21.63.",
        "$21 to $21.63/hr",
        "hour",
    ),
    ("Pay Details:\n$30.74 - $30.74 USD\n", "$30.74/hr", "hour"),
    ("salary range: $125,300 - $178,900\nBonus eligible: Yes", "$125k to $179k", "year"),
    ("salary range for this position is USD$110,000.00 - USD$138,000.00 .", "$110k to $138k", "year"),
    ("Base Pay Range (USD)\n129,100 - 191,030, $ per annum", "$129k to $191k", "year"),
    ("The base pay range for this role is $45 per hour.", "$45/hr", "hour"),
    ("Pay Range: \n\n- AZ (Chandler, Phoenix): $48.08 Hourly", "$48.08/hr", "hour"),
    ("salary range for this position is $124800 to $124800 USD per year", "$125k", "year"),
    (
        "The pay range for this position is $75,000 - $95,000 which includes a base salary and bonus.",
        "$75k to $95k",
        "year",
    ),
]


@pytest.mark.parametrize("text,label,period", CASES)
def test_reads_pay_ranges(text, label, period):
    got = salary.extract(text)
    assert got and got["text"] == label and got["period"] == period


@pytest.mark.parametrize(
    "text",
    [
        "total fiscal year 2025 sales of more than $86 billion. Lowe's employs approximately 300,000 associates",
        "responsible for over $200B in client assets and serves 1.3 million investors",
        "Student loan repayment program up to $10k, Company paid life and disability plans",
        "The current base annual salary range for this role is currently:\n$0-0\nPay scales are determined",
        "a sign-on bonus of $10,000 - $15,000 for eligible hires",
        "from 2020 - 2024 the team grew",
        "eligible for a $10,000 - $15,000 sign-on bonus",
        "no pay information at all",
    ],
)
def test_ignores_money_that_is_not_pay(text):
    assert salary.extract(text) is None


def test_several_locations_span_lowest_to_highest():
    text = (
        "Bentonville, Arkansas: The annual salary range for this position is $90,000.00 - $180,000.00\n"
        "Sunnyvale, California: The annual salary range for this position is $112,000.00 - $224,000.00"
    )
    got = salary.extract(text)
    assert got["text"] == "$90k to $224k" and got["multiple"]


def test_sentence_holding_the_first_pay_figure():
    text = "Great team. The base salary range is $120,000 - $150,000 per year. Bonus eligible.\nApply by Friday."
    assert salary.sentence(text) == "The base salary range is $120,000 - $150,000 per year."
    assert salary.sentence("No pay here, 401(k) match only.") is None
