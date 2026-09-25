"""Hiring-email rules: automatic only with exactly one matching req id and clear wording; the rest goes to review."""

from radar import mailmatch

APPS = [
    {"company": "Capital One", "req_id": "R1001740", "title": "AI Engineer 3"},
    {"company": "GM", "req_id": "JR-202619337", "title": "Data Engineer"},
    {"company": "Walmart", "req_id": "R-2331482", "title": "Data Scientist III"},
    {"company": "Walmart", "req_id": "R-2023715", "title": "Data Engineer III"},
    {"company": "HP", "req_id": "1234", "title": "Data Analyst"},
]


def mail(subject, body, sender="Capital One <capitalone@myworkday.com>"):
    return {"sender": sender, "subject": subject, "body": body}


def test_confirmation_with_req_id_updates():
    d = mailmatch.decide(mail("Thank you for applying", "We received your application for R1001740."), APPS)
    assert d["action"] == "update" and d["req_id"] == "R1001740" and d["status"] == "applied"


def test_rejection_wins_over_thank_you():
    body = "Thank you for applying to R1001740. Unfortunately we have decided to move forward with other candidates."
    assert mailmatch.decide(mail("Your application", body), APPS)["status"] == "rejected"


def test_phone_screen_is_screen_and_interview_is_interview():
    assert (
        mailmatch.decide(mail("Next steps", "Let us set up a phone screen for R1001740."), APPS)["status"] == "screen"
    )
    assert (
        mailmatch.decide(mail("Invitation", "We would like to interview you for R1001740."), APPS)["status"]
        == "interview"
    )


def test_req_id_without_hyphen_still_matches():
    d = mailmatch.decide(mail("Application received", "Req JR202619337 received.", "GM <gm@myworkday.com>"), APPS)
    assert d["action"] == "update" and d["company"] == "GM"


def test_longer_number_is_not_a_match():
    d = mailmatch.decide(mail("Thank you for applying", "Reference R10017401 for your records."), APPS)
    assert d["action"] == "review" and d["req_id"] is None  # hiring mail from Capital One, but no matching id


def test_no_req_id_goes_to_review_with_a_guess():
    d = mailmatch.decide(
        mail("Your Capital One application", "We regret to inform you the position has been filled."), APPS
    )
    assert d["action"] == "review" and d["status"] == "rejected" and d["reason"] == "no req id"
    assert (d["company"], d["req_id"]) == ("Capital One", "R1001740")


def test_two_applications_at_one_company_leave_the_choice_to_rohan():
    body = "We have decided to move forward with other candidates."
    d = mailmatch.decide(mail("Walmart update", body, "Walmart <walmart@myworkday.com>"), APPS)
    assert d["action"] == "review" and d["company"] is None
    assert {c["req_id"] for c in d["candidates"]} == {"R-2331482", "R-2023715"}  # listed first in the menu


def test_req_id_with_unclear_wording_goes_to_review():
    d = mailmatch.decide(mail("Update on R1001740", "Please see the attached document."), APPS)
    assert d["action"] == "review" and d["req_id"] == "R1001740" and d["status"] is None


def test_two_req_ids_go_to_review():
    d = mailmatch.decide(mail("Thank you for applying", "Roles R-2331482 and R-2023715 received."), APPS)
    assert d["action"] == "review" and "2 req ids" in d["reason"]


def test_newsletters_and_short_ids_are_ignored():
    assert mailmatch.decide(mail("Weekly deals", "Save 20% this week", "Store <deals@shop.com>"), APPS) is None
    assert (
        mailmatch.decide(mail("Order 1234 shipped", "Thank you for your interest", "Shop <x@shop.com>"), APPS) is None
    )
