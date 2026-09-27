"""Decide what a hiring email means for the applications. Pure functions: no mailbox, no files.

Rule agreed with the owner (2026-09-25): a status changes on its own only when the email contains the requisition id of
exactly one application and its wording is clear. Widened for rejections on 2026-09-27 at the owner's request: a
rejection without an id moves the one application whose role it names (radar/rolematch.py), and a rejection for a
role that is not on the list is filed apart instead of waiting for review. Other emails that could change a status
still go to review.

Calibrated on the owner's first real run: confirmation emails mention interviews as a possible next step ("if you are
selected for an interview"), so interview and screen need invitation wording, and any phrase that follows "if",
"may" or "should" nearby is ignored."""

import re

from radar import rolematch

STATUS_RULES = {
    "rejected": r"other candidates|not (?:be )?mov(?:e|ing) forward|decided (?:to )?(?:pursue|proceed|move forward) with|"
    r"(?:were|have been|was) not selected|not been selected|regret to inform|no longer (?:under consideration|being considered)|"
    r"position has been filled|unable to (?:offer|move (?:you |your application )?forward)|will not be (?:moving|proceeding)|"
    r"won't be moving forward|can(?:not|'t| not) move forward|"
    # Added after a real "have decided not to move forward for the ... role" rejection read as a confirmation.
    r"(?:decided|chosen|elected) not to|not (?:be )?(?:progressing|advancing|proceeding) (?:with )?your|"
    r"not able to (?:offer|move|progress|proceed)|(?:selected|chosen|hired) (?:another|a different) (?:candidate|applicant)|"
    r"(?:another|other) (?:qualified )?applicants|(?:role|position|requisition) (?:has been|was) (?:filled|closed|cancell?ed)|"
    r"(?:aren't|are not|is not|isn't|won't be|will not be) (?:able to )?(?:mov(?:e|ing) (?:you |your application )?forward|"
    r"proceed(?:ing)?|progress(?:ing)?|consider(?:ing)?|pursu(?:e|ing))|regret to (?:inform|share|let you know|advise)|"
    r"(?:does|do) not (?:align|match) (?:as )?(?:closely )?with",
    "offer": r"pleased to offer|offer letter|extend(?:ing)? (?:you )?an offer|offer of employment",
    "screen": r"(?:schedule|book|set up|complete) (?:a |an |your )?(?:phone screen|recruiter (?:call|screen)|initial (?:call|screen))|"
    r"invit(?:e|ed|ation) (?:you )?to (?:complete|take) (?:an? |the )?(?:online |technical |coding )?(?:assessment|challenge|test)|"
    r"your (?:hackerrank|codility|codesignal|coding) (?:assessment|test|challenge)",
    "interview": r"(?:like|love|want) to (?:invite you to |schedule |set up |arrange )?(?:an? )?interview|"
    r"invit(?:e|ed|ation) (?:you )?(?:to|for) (?:an? |the )?(?:virtual |onsite |on-site |phone )?interview|"
    r"interview (?:invitation|request|confirmation)|your interview (?:is|has been) (?:scheduled|confirmed)|"
    r"(?:schedule|book|select a time for) your interview",
    "applied": r"thank you for (?:applying|your application|your interest)|thanks for applying|(?:we have |we've )?received your application|"
    r"application (?:has been |was )?(?:received|submitted)|successfully (?:applied|submitted)",
}
STATUS_RES = {s: re.compile(p, re.I) for s, p in STATUS_RULES.items()}
# A phrase shortly after one of these words describes something that might happen, not something that did.
CONDITIONAL = re.compile(r"\b(?:if|may|might|should|in the event|whether)\b", re.I)
ATS_SENDERS = re.compile(
    r"myworkday|workday|greenhouse|lever\.co|icims|smartrecruiters|successfactors|taleo|ashby|jobvite", re.I
)


def statuses(text):
    """Every status whose wording appears in the text, ignoring conditional mentions."""
    found, text = set(), (text or "").replace("’", "'")  # a curly apostrophe, as in "can't", reads as straight
    for status, rx in STATUS_RES.items():
        for m in rx.finditer(text):
            if not CONDITIONAL.search(text[max(0, m.start() - 45) : m.start()]):
                found.add(status)
                break
    return found


def classify(text):
    """(status, clear). A rejection or offer is decisive. An invitation inside a confirmation is not clear."""
    s = statuses(text)
    for decisive in ("rejected", "offer"):
        if decisive in s:
            return decisive, True
    step = "interview" if "interview" in s else "screen" if "screen" in s else None
    if step:
        return step, "applied" not in s
    return ("applied", True) if "applied" in s else (None, False)


def _id_rx(req_id):
    variants = {req_id, req_id.replace("-", "")}
    alts = "|".join(re.escape(v) for v in sorted(variants, key=len, reverse=True) if v)
    return re.compile(rf"(?<![A-Za-z0-9])(?:{alts})(?![A-Za-z0-9])", re.I)


def by_req_id(text, apps):
    """Applications whose requisition id appears in the text as a whole token. Ids shorter than 5 are ignored."""
    return [a for a in apps if len(a["req_id"]) >= 5 and _id_rx(a["req_id"]).search(text)]


def by_company(text, apps):
    """Applications whose company name appears in the text, used only to pre-fill a needs-review suggestion."""
    return [a for a in apps if re.search(rf"(?<![A-Za-z]){re.escape(a['company'])}(?![A-Za-z])", text, re.I)]


def sender_company(sender, tenants):
    """The employer behind a Workday sender such as pwc@myworkday.com, from companies.json tenants, or None."""
    m = re.search(r"([\w.-]+)@myworkday\.com", sender or "", re.I)
    return tenants.get(m.group(1).lower()) if m else None


def decide(msg, apps, tenants=None):
    """msg has sender, subject, body. Returns None to ignore the email, else a dict with action "update" or "review".
    Emails that cannot move a status past "applied" (confirmations, account and password mail) are ignored.
    tenants maps a Workday tenant to the employer name, so a review guess can come from the sender address."""
    text = f"{msg.get('subject', '')}\n{msg.get('body', '')}"
    status, clear = classify(text)
    if status is None:
        return None
    hits = by_req_id(text, apps)
    if len(hits) == 1 and clear:
        a = hits[0]
        return {
            "action": "update",
            "company": a["company"],
            "req_id": a["req_id"],
            "status": status,
            "reason": "req id",
        }
    if status == "applied":
        return None  # a confirmation: every tracked application is already at applied
    if hits:
        a = hits[0] if len(hits) == 1 else None
        return _review(status, a, "req id found, wording mixed" if a else f"{len(hits)} req ids found", hits)
    sender = msg.get("sender", "")
    if not (ATS_SENDERS.search(sender) or by_company(f"{sender} {msg.get('subject', '')}", apps)):
        return None  # not recognisably about an application
    # A Workday sender address names the employer; when it does, guess only among that employer's applications
    # (none if the owner never applied there). Otherwise the sender and subject, then the body: every Workday email
    # names Workday in its footer, so the body comes last.
    employer = sender_company(sender, tenants or {})
    if employer:
        guesses = [a for a in apps if a["company"] == employer]
    else:
        guesses = by_company(f"{sender} {msg.get('subject', '')}", apps) or by_company(text, apps)
    if status == "rejected":
        found = _rejection(msg, employer, guesses, apps)
        if found:
            return found
    return _review(status, guesses[0] if len(guesses) == 1 else None, "no req id", guesses)


def _rejection(msg, employer, guesses, apps):
    """A rejection without a usable id: the application whose role the email names, or "untracked" when the email
    names a role that is not on the list or the employer has nothing open. None leaves it for review."""
    pool = [a for a in apps if a["company"] == employer] if employer else guesses
    text = rolematch.head(msg.get("subject"), msg.get("body"))
    hits = rolematch.by_title(text, pool)
    if len(hits) == 1:
        a = hits[0]
        if a.get("status") == "rejected":
            return {"action": "ignore"}  # already recorded, usually by an earlier email about the same role
        return {
            "action": "update",
            "company": a["company"],
            "req_id": a["req_id"],
            "status": "rejected",
            "reason": "title",
        }
    if len(hits) > 1:
        return _review("rejected", None, "several applications share this title", hits)
    live = [a for a in pool if a.get("status", "applied") not in ("rejected", "offer")]
    role = rolematch.named_role(text)
    if role or not live:
        company = employer or (guesses[0]["company"] if guesses else None)
        return {
            "action": "untracked",
            "status": "rejected",
            "company": company,
            "role": role,
            "reason": "not on your list",
        }
    return None


def _review(status, app, why, candidates=()):
    """A needs-review item. candidates are applications the email may be about, listed first in the page's menu."""
    return {
        "action": "review",
        "status": status,
        "company": app and app["company"],
        "req_id": app and app["req_id"],
        "reason": why,
        "candidates": [{"company": c["company"], "req_id": c["req_id"]} for c in candidates][:10],
    }
