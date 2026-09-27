"""Hiring-email rules: automatic only with exactly one matching req id and clear wording; other emails that could
change a status go to review; confirmations and account mail are ignored."""

import pytest

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


def test_confirmation_with_req_id_updates_to_applied():
    d = mailmatch.decide(mail("Thank you for applying", "We received your application for R1001740."), APPS)
    assert d["action"] == "update" and d["req_id"] == "R1001740" and d["status"] == "applied"


def test_rejection_wins_over_thank_you():
    body = "Thank you for applying to R1001740. Unfortunately we have decided to move forward with other candidates."
    assert mailmatch.decide(mail("Your application", body), APPS)["status"] == "rejected"


def test_invitations_to_screen_and_interview():
    d = mailmatch.decide(mail("Next steps", "Please schedule a phone screen for R1001740."), APPS)
    assert d["action"] == "update" and d["status"] == "screen"
    d = mailmatch.decide(mail("Invitation", "We would like to invite you to interview for R1001740."), APPS)
    assert d["action"] == "update" and d["status"] == "interview"


def test_invitation_inside_a_confirmation_goes_to_review():
    body = "Thank you for applying to R1001740. We would like to invite you to interview next week."
    d = mailmatch.decide(mail("Next steps", body), APPS)
    assert d["action"] == "review" and d["status"] == "interview" and d["req_id"] == "R1001740"


def test_req_id_without_hyphen_still_matches():
    d = mailmatch.decide(mail("Application received", "Req JR202619337 received.", "GM <gm@myworkday.com>"), APPS)
    assert d["action"] == "update" and d["company"] == "GM"


def test_longer_number_is_not_a_match():
    d = mailmatch.decide(mail("Update", "We regret to inform you. Reference R10017401."), APPS)
    assert d["action"] == "review" and d["reason"] == "no req id"  # a guess to confirm, never an automatic update


def test_rejection_without_req_id_goes_to_review_with_a_guess():
    d = mailmatch.decide(
        mail("Your Capital One application", "We regret to inform you the position has been filled."), APPS
    )
    assert d["action"] == "review" and d["status"] == "rejected" and d["reason"] == "no req id"
    assert (d["company"], d["req_id"]) == ("Capital One", "R1001740")


def test_two_applications_at_one_company_list_both_first():
    body = "We have decided to move forward with other candidates."
    d = mailmatch.decide(mail("Walmart update", body, "Walmart <walmart@myworkday.com>"), APPS)
    assert d["action"] == "review" and d["company"] is None
    assert {c["req_id"] for c in d["candidates"]} == {"R-2331482", "R-2023715"}


def test_two_req_ids_go_to_review():
    d = mailmatch.decide(mail("Update", "For R-2331482 and R-2023715 we regret to inform you."), APPS)
    assert d["action"] == "review" and "2 req ids" in d["reason"]


def test_mail_that_cannot_change_a_status_is_ignored():
    assert mailmatch.decide(mail("Update on R1001740", "Please see the attached document."), APPS) is None
    assert mailmatch.decide(mail("Verify your candidate account", "Code for R1001740: 482913"), APPS) is None
    assert mailmatch.decide(mail("Thank you for applying!", "We received your application."), APPS) is None
    assert mailmatch.decide(mail("Weekly deals", "Save 20% this week", "Store <deals@shop.com>"), APPS) is None


# Paraphrases of boilerplate from real confirmation emails that the first version misread (2026-09-25).
@pytest.mark.parametrize(
    "body",
    [
        "Thank you for applying. You will be contacted if you're selected for an interview.",
        "We received your application. If you are selected to move forward in the interview process, we will reach out.",
        "Application received. You'll find resources like interview tips while you wait.",
        "Thank you for your interest. We will contact you to arrange an interview if the role is a good match.",
        "Thanks for applying. Based on your skills, you may receive an invitation to take a coding assessment.",
        "Thank you for your application. If you are not selected for this position, keep an eye on our jobs page.",
        "We received your application. Let us know if you need adjustments when applying and interviewing.",
    ],
)
def test_confirmation_boilerplate_is_not_a_status_change(body):
    d = mailmatch.decide(mail("Thank you for applying", f"{body} Req R1001740."), APPS)
    assert d["action"] == "update" and d["status"] == "applied"  # forward-only, so this changes nothing


@pytest.mark.parametrize(
    "body",
    [
        "We are unable to move you forward to the next step in the recruiting process.",
        "Unfortunately, we can’t move forward with your application.",
        "This is to notify you that you were not selected to proceed to the next stage.",
    ],
)
def test_real_rejection_wordings(body):
    assert mailmatch.classify(body) == ("rejected", True)


# Real rejection wordings the second version missed (five real rejections, 2026-09-25).
@pytest.mark.parametrize(
    "body",
    [
        "We have reviewed your application and have decided not to move forward for the R0000001 role at this time.",
        "Unfortunately, as visa sponsorship is not available for this position, we won't be able to move forward.",
        "Unfortunately, we regret to share that we aren't moving forward with your application.",
        "While your experience is impressive, unfortunately, it does not align as closely with what our team is seeking.",
        "At this time we are pursuing other applicants.",
        "We will not be moving you forward in the process for this position.",
    ],
)
def test_more_rejection_wordings(body):
    assert mailmatch.classify(body) == ("rejected", True)


def test_review_guess_prefers_sender_and_subject_over_footer():
    apps = APPS + [{"company": "Workday", "req_id": "JR-0109848", "title": "Data Engineer"}]
    body = "We regret to inform you that we will not be proceeding. Powered by Workday."
    d = mailmatch.decide(mail("Capital One job application: update", body, "Capital One <c@myworkday.com>"), apps)
    assert d["action"] == "review" and d["company"] == "Capital One"


def test_workday_sender_address_names_the_employer():
    tenants = {"pwc": "PwC", "capitalone": "Capital One"}
    apps = APPS + [{"company": "Workday", "req_id": "JR-0109848", "title": "Data Engineer"}]
    body = "We regret to inform you that we will not be proceeding. Powered by Workday."
    not_tracked = mailmatch.decide(mail("Job application: update", body, "pwc@myworkday.com"), apps, tenants)
    assert not_tracked["action"] == "untracked" and not_tracked["company"] == "PwC"  # never applied to PwC
    tracked = mailmatch.decide(mail("Job application: update", body, "capitalone@myworkday.com"), apps, tenants)
    assert tracked["company"] == "Capital One"


# Rejections without a requisition id, worded like the owner's real ones (2026-09-27): matched by the role they name.
TRACKED = [
    {"company": "Mastercard", "req_id": "R-288332", "title": "Senior Data Engineer", "status": "applied"},
    {"company": "Mastercard", "req_id": "R-289305", "title": "Data Engineer II", "status": "applied"},
    {"company": "Mastercard", "req_id": "R-291128", "title": "Data Scientist", "status": "applied"},
    {"company": "Expedia", "req_id": "R-109347", "title": "Machine Learning Scientist II", "status": "applied"},
    {
        "company": "Expedia",
        "req_id": "R-109446",
        "title": "Machine Learning Scientist II - Agentic Experiences",
        "status": "applied",
    },
    {"company": "Walmart", "req_id": "R-2648464", "title": "(USA) Senior, Data Scientist", "status": "applied"},
    {"company": "Walmart", "req_id": "R-2641183", "title": "Senior Data Scientist", "status": "applied"},
    {"company": "Cisco", "req_id": "2020310", "title": "Forward Deployed Engineer- Splunk", "status": "rejected"},
    {"company": "LexisNexis", "req_id": "R118426", "title": "Fraud Data Analyst", "status": "applied"},
]
TENANTS = {"mastercard": "Mastercard", "expedia": "Expedia", "cisco": "Cisco", "relx": "LexisNexis", "truist": "Truist"}
NO = " After careful consideration, we have decided to move forward with other candidates."


def reject(sender, body, subject="An update on your application"):
    return mailmatch.decide(mail(subject, body + NO, sender), TRACKED, TENANTS)


def test_rejection_names_the_role_and_moves_that_application():
    d = reject(
        "MasterCard People Services <mastercard@myworkday.com>",
        "Thank you for applying to the Senior Data Engineer position.",
    )
    assert (d["action"], d["req_id"], d["reason"]) == ("update", "R-288332", "title")
    d = reject("mastercard@myworkday.com", "Thank you for applying to the Data Engineer II position.")
    assert d["req_id"] == "R-289305"


def test_a_shorter_title_inside_a_longer_one_is_not_a_match():
    # "Data Scientist" is a Mastercard application; "Senior Data Scientist" is not, so nothing matches by title.
    d = reject("mastercard@myworkday.com", "Thank you for applying to the Senior Data Scientist position.")
    assert d["action"] == "untracked" and d["role"] == "Senior Data Scientist"
    d = reject("expedia@myworkday.com", "Thank you for applying for the Machine Learning Scientist II position.")
    assert d["req_id"] == "R-109347"  # not the "II - Agentic Experiences" one


def test_role_not_on_the_list_is_filed_apart():
    d = reject("relx@myworkday.com", "We appreciate the time you invested in applying for the Data Scientist opening.")
    assert (d["action"], d["company"], d["role"]) == ("untracked", "LexisNexis", "Data Scientist")
    d = reject(
        "Truist@myworkday.com", "Thank you for applying for the Data Scientist I - Card Fraud position at Truist."
    )
    assert d["action"] == "untracked" and d["company"] == "Truist"
    d = reject(
        "Recruiting @ Perplexity <no-reply@ashbyhq.com>",
        "Thank you for your interest in the Member of Technical Staff (Data Scientist, Evals) role.",
    )
    assert d["action"] == "untracked"


def test_rejection_for_an_application_already_rejected_is_ignored():
    d = reject("Cisco@myworkday.com", "Thank you for applying to the Forward Deployed Engineer- Splunk position.")
    assert d == {"action": "ignore"}


def test_same_title_twice_still_asks():
    d = reject("noreply@walmart.com", "Thank you for applying to the Senior Data Scientist position at Walmart.")
    assert d["action"] == "review" and {c["req_id"] for c in d["candidates"]} == {"R-2648464", "R-2641183"}


def test_footer_job_suggestions_do_not_count():
    body = "Thank you for your interest in Mastercard." + " " * 1600 + "Jobs you may like: Data Scientist, New York."
    d = reject("mastercard@myworkday.com", body)
    assert d["action"] == "review"  # three open Mastercard applications, no role named up top
