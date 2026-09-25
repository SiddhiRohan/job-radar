"""Decide what a hiring email means for the applications. Pure functions: no mailbox, no files.

Rule agreed with Rohan (2026-09-25): a status changes on its own only when the email contains the requisition id of
exactly one application and its wording is clear. Every other hiring email goes to a needs-review list."""

import re

# Checked in this order: a rejection often also says "thank you for applying", and a phone screen is an interview.
STATUS_RULES = [
    (
        "rejected",
        r"other candidates|not (?:be )?mov(?:e|ing) forward|decided to (?:pursue|proceed|move forward) with|"
        r"not (?:been )?selected|regret to inform|no longer (?:under consideration|being considered)|"
        r"position has been filled|unable to (?:offer|move forward)|will not be (?:moving|proceeding)",
    ),
    ("offer", r"pleased to offer|offer letter|extend(?:ing)? (?:you )?an offer|offer of employment"),
    (
        "screen",
        r"phone screen|recruiter (?:call|screen)|initial (?:call|conversation|screen)|"
        r"(?:online|technical|coding) assessment|hackerrank|codility|codesignal|take[- ]home",
    ),
    ("interview", r"\binterview"),
    (
        "applied",
        r"thank you for (?:applying|your application|your interest)|(?:we have |we've )?received your application|"
        r"application (?:has been |was )?(?:received|submitted)|successfully (?:applied|submitted)",
    ),
]
STATUS_RES = [(s, re.compile(p, re.I)) for s, p in STATUS_RULES]
ATS_SENDERS = re.compile(
    r"myworkday|workday|greenhouse|lever\.co|icims|smartrecruiters|successfactors|taleo|ashby|jobvite", re.I
)


def status_of(text):
    """The status the wording points to, or None."""
    for status, rx in STATUS_RES:
        if rx.search(text or ""):
            return status
    return None


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


def decide(msg, apps):
    """msg has sender, subject, body. Returns None to ignore the email, else a dict with action "update" or "review"."""
    text = f"{msg.get('subject', '')}\n{msg.get('body', '')}"
    status, hits = status_of(text), by_req_id(text, apps)
    if len(hits) == 1 and status:
        a = hits[0]
        return {
            "action": "update",
            "company": a["company"],
            "req_id": a["req_id"],
            "status": status,
            "reason": "req id",
        }
    if hits:  # an id matched but the wording is unclear, or several ids matched
        a = hits[0] if len(hits) == 1 else None
        why = "req id found, status unclear" if a else f"{len(hits)} req ids found"
        return _review(status, a, why, hits)
    hiring = ATS_SENDERS.search(msg.get("sender", "")) or by_company(
        f"{msg.get('sender', '')} {msg.get('subject', '')}", apps
    )
    if not (hiring and status):
        return None  # not recognisably about an application
    guesses = by_company(text, apps)
    one = guesses[0] if len(guesses) == 1 else None
    return _review(status, one, "no req id", guesses)


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
