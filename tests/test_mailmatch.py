"""Hiring-email rules: automatic only with exactly one matching req id and clear wording; other emails that could
change a status go to review; confirmations and account mail are ignored."""

import pytest

from radar import mailmatch

APPS = [
    {"company": "Northwind", "req_id": "R1000001", "title": "AI Engineer 3"},
    {"company": "Lamna", "req_id": "JR-202600001", "title": "Data Engineer"},
    {"company": "Woodgrove", "req_id": "R-300003", "title": "Data Scientist III"},
    {"company": "Woodgrove", "req_id": "R-300004", "title": "Data Engineer III"},
    {"company": "Trey", "req_id": "1234", "title": "Data Analyst"},
]


def mail(subject, body, sender="Northwind <northwind@myworkday.com>"):
    return {"sender": sender, "subject": subject, "body": body}


def test_confirmation_with_req_id_updates_to_applied():
    d = mailmatch.decide(mail("Thank you for applying", "We received your application for R1000001."), APPS)
    assert d["action"] == "update" and d["req_id"] == "R1000001" and d["status"] == "applied"


def test_rejection_wins_over_thank_you():
    body = "Thank you for applying to R1000001. Unfortunately we have decided to move forward with other candidates."
    assert mailmatch.decide(mail("Your application", body), APPS)["status"] == "rejected"


def test_invitations_to_screen_and_interview():
    d = mailmatch.decide(mail("Next steps", "Please schedule a phone screen for R1000001."), APPS)
    assert d["action"] == "update" and d["status"] == "screen"
    d = mailmatch.decide(mail("Invitation", "We would like to invite you to interview for R1000001."), APPS)
    assert d["action"] == "update" and d["status"] == "interview"


def test_invitation_inside_a_confirmation_goes_to_review():
    body = "Thank you for applying to R1000001. We would like to invite you to interview next week."
    d = mailmatch.decide(mail("Next steps", body), APPS)
    assert d["action"] == "review" and d["status"] == "interview" and d["req_id"] == "R1000001"


def test_req_id_without_hyphen_still_matches():
    d = mailmatch.decide(mail("Application received", "Req JR202600001 received.", "Lamna <lamna@myworkday.com>"), APPS)
    assert d["action"] == "update" and d["company"] == "Lamna"


def test_longer_number_is_not_a_match():
    d = mailmatch.decide(mail("Update", "We regret to inform you. Reference R10000011."), APPS)
    assert d["action"] == "review" and d["reason"] == "no req id"  # a guess to confirm, never an automatic update


def test_rejection_without_req_id_goes_to_review_with_a_guess():
    d = mailmatch.decide(
        mail("Your Northwind application", "We regret to inform you the position has been filled."), APPS
    )
    assert d["action"] == "review" and d["status"] == "rejected" and d["reason"] == "no req id"
    assert (d["company"], d["req_id"]) == ("Northwind", "R1000001")


def test_two_applications_at_one_company_list_both_first():
    body = "We have decided to move forward with other candidates."
    d = mailmatch.decide(mail("Woodgrove update", body, "Woodgrove <woodgrove@myworkday.com>"), APPS)
    assert d["action"] == "review" and d["company"] is None
    assert {c["req_id"] for c in d["candidates"]} == {"R-300003", "R-300004"}


def test_two_req_ids_go_to_review():
    d = mailmatch.decide(mail("Update", "For R-300003 and R-300004 we regret to inform you."), APPS)
    assert d["action"] == "review" and "2 req ids" in d["reason"]


def test_mail_that_cannot_change_a_status_is_ignored():
    assert mailmatch.decide(mail("Update on R1000001", "Please see the attached document."), APPS) is None
    assert mailmatch.decide(mail("Verify your candidate account", "Code for R1000001: 482913"), APPS) is None
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
    d = mailmatch.decide(mail("Thank you for applying", f"{body} Req R1000001."), APPS)
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
    apps = APPS + [{"company": "Workday", "req_id": "JR-0000123", "title": "Data Engineer"}]
    body = "We regret to inform you that we will not be proceeding. Powered by Workday."
    d = mailmatch.decide(mail("Northwind job application: update", body, "Northwind <c@myworkday.com>"), apps)
    assert d["action"] == "review" and d["company"] == "Northwind"


def test_workday_sender_address_names_the_employer():
    tenants = {"fabrikam": "Fabrikam", "northwind": "Northwind"}
    apps = APPS + [{"company": "Workday", "req_id": "JR-0000123", "title": "Data Engineer"}]
    body = "We regret to inform you that we will not be proceeding. Powered by Workday."
    not_tracked = mailmatch.decide(mail("Job application: update", body, "fabrikam@myworkday.com"), apps, tenants)
    assert not_tracked["action"] == "untracked" and not_tracked["company"] == "Fabrikam"  # never applied to Fabrikam
    tracked = mailmatch.decide(mail("Job application: update", body, "northwind@myworkday.com"), apps, tenants)
    assert tracked["company"] == "Northwind"


# Rejections without a requisition id, worded like the owner's real ones (2026-09-27): matched by the role they name.
TRACKED = [
    {"company": "Contoso", "req_id": "R-100001", "title": "Senior Data Engineer", "status": "applied"},
    {"company": "Contoso", "req_id": "R-100002", "title": "Data Engineer II", "status": "applied"},
    {"company": "Contoso", "req_id": "R-100003", "title": "Data Scientist", "status": "applied"},
    {"company": "Tailspin", "req_id": "R-200001", "title": "Machine Learning Scientist II", "status": "applied"},
    {
        "company": "Tailspin",
        "req_id": "R-200002",
        "title": "Machine Learning Scientist II - Search",
        "status": "applied",
    },
    {"company": "Woodgrove", "req_id": "R-300001", "title": "(USA) Senior, Data Scientist", "status": "applied"},
    {"company": "Woodgrove", "req_id": "R-300002", "title": "Senior Data Scientist", "status": "applied"},
    {"company": "Adatum", "req_id": "4000001", "title": "Forward Deployed Engineer", "status": "rejected"},
    {"company": "Litware", "req_id": "R500001", "title": "Fraud Data Analyst", "status": "applied"},
]
TENANTS = {
    "contoso": "Contoso",
    "tailspin": "Tailspin",
    "adatum": "Adatum",
    "litware": "Litware",
    "proseware": "Proseware",
}
NO = " After careful consideration, we have decided to move forward with other candidates."


def reject(sender, body, subject="An update on your application"):
    return mailmatch.decide(mail(subject, body + NO, sender), TRACKED, TENANTS)


def test_rejection_names_the_role_and_moves_that_application():
    d = reject(
        "Contoso People Services <contoso@myworkday.com>",
        "Thank you for applying to the Senior Data Engineer position.",
    )
    assert (d["action"], d["req_id"], d["reason"]) == ("update", "R-100001", "title")
    d = reject("contoso@myworkday.com", "Thank you for applying to the Data Engineer II position.")
    assert d["req_id"] == "R-100002"


def test_a_shorter_title_inside_a_longer_one_is_not_a_match():
    # "Data Scientist" is a Contoso application; "Senior Data Scientist" is not, so nothing matches by title.
    d = reject("contoso@myworkday.com", "Thank you for applying to the Senior Data Scientist position.")
    assert d["action"] == "untracked" and d["role"] == "Senior Data Scientist"
    d = reject("tailspin@myworkday.com", "Thank you for applying for the Machine Learning Scientist II position.")
    assert d["req_id"] == "R-200001"  # not the "II - Agentic Experiences" one


def test_role_not_on_the_list_is_filed_apart():
    d = reject(
        "litware@myworkday.com", "We appreciate the time you invested in applying for the Data Scientist opening."
    )
    assert (d["action"], d["company"], d["role"]) == ("untracked", "Litware", "Data Scientist")
    d = reject(
        "Proseware@myworkday.com", "Thank you for applying for the Data Scientist I - Card Fraud position at Proseware."
    )
    assert d["action"] == "untracked" and d["company"] == "Proseware"
    d = reject(
        "Recruiting @ Wingtip <no-reply@ashbyhq.com>",
        "Thank you for your interest in the Member of Technical Staff (Data Scientist) role.",
    )
    assert d["action"] == "untracked"


def test_rejection_for_an_application_already_rejected_is_ignored():
    d = reject("Adatum@myworkday.com", "Thank you for applying to the Forward Deployed Engineer position.")
    assert d == {"action": "ignore"}


def test_same_title_twice_still_asks():
    d = reject("noreply@woodgrove.com", "Thank you for applying to the Senior Data Scientist position at Woodgrove.")
    assert d["action"] == "review" and {c["req_id"] for c in d["candidates"]} == {"R-300001", "R-300002"}


def test_footer_job_suggestions_do_not_count():
    body = "Thank you for your interest in Contoso." + " " * 1600 + "Jobs you may like: Data Scientist, New York."
    d = reject("contoso@myworkday.com", body)
    assert d["action"] == "review"  # three open Contoso applications, no role named up top


def test_role_phrase_after_a_false_start():
    from radar import rolematch

    text = "Thank you for your interest in Woodgrove. We appreciate the time you took to apply for the (USA) Data Scientist III position."
    assert rolematch.named_role(text) == "(USA) Data Scientist III"
