"""The fit, factor by factor, for the posting drawer: the model's four (radar/fit.py) and three read here by rule from
the stored posting, with no model call: sponsorship, location and pay. Sponsorship uses the digest's own test, so its
badge always agrees with the section the posting sits in."""

import re

from radar import digest, fit, salary

# Workday location strings say "Remote - USA", "US-Remote", "Virtual", "Hybrid". A description counts only with
# unambiguous wording, not negated just before: "remote sensing", "hybrid cloud" and "not remote-eligible" do not.
REMOTE = re.compile(r"\b(?:remote|virtual|telecommut\w*|work from home|home[- ]based)\b", re.I)
HYBRID = re.compile(r"\bhybrid\b", re.I)
REMOTE_TEXT = re.compile(
    r"\b(?:fully|100%) remote\b|\bremote[- ](?:first|eligible)\b|\b(?:role|position|job) is remote\b", re.I
)
HYBRID_TEXT = re.compile(r"\bhybrid (?:work|schedule|arrangement)|\b(?:role|position|job) is hybrid\b", re.I)
NEGATED = re.compile(r"\b(?:not|non|no)\b[\s-]*(?:an?\s+)?$", re.I)


def offers(rx, text):
    """The wording appears at least once without "not", "non" or "no" right before it."""
    return any(not NEGATED.search(text[max(0, m.start() - 12) : m.start()]) for m in rx.finditer(text))


def clip(text, words=20):
    """At most `words` words, with an ellipsis when cut: evidence phrases are sentence windows, often longer."""
    parts = (text or "").split()
    return " ".join(parts[:words]) + (" …" if len(parts) > words else "")


def _row(factor, verdict, posting, note):
    return {"factor": factor, "verdict": verdict, "posting": posting, "resume": "", "note": note, "rule": True}


def sponsorship(j):
    """Gap when the digest would skip the posting, meets when it counts as sponsoring, partial otherwise."""
    v = j.get("verdict") or {}
    tag, model = j.get("sponsorship") or "unknown", v.get("sponsorship")
    if tag == "no":
        note = "The posting rules out sponsorship, or asks for citizenship or a clearance."
    elif tag == "perm_ad":
        note = "Reads as a PERM ad written for one candidate, not an open role."
    elif model == "no":
        note = "The model read the posting as not sponsoring."
    elif tag == "yes":
        note = "The posting says it sponsors."
    elif model == "yes":
        note = "The model read the posting as sponsoring."
    elif tag in ("likely", "unlikely"):
        note = f"The posting is silent; the company default is {'yes' if tag == 'likely' else 'no'}."
    else:
        note = "Neither the posting nor the company default says."
    verdict = "gap" if digest.says_no(j) else "meets" if digest.sponsors(j) else "partial"
    said = j.get("sponsorship_evidence") or v.get("sponsorship_evidence")
    return _row("sponsorship", verdict, clip(said) or "Not stated", note)


def location(j):
    """Where the role is, and whether it is remote or hybrid. Any US location meets: no location preference is set."""
    where = j.get("detail_location") or j.get("location") or ""
    others = [x for x in j.get("additional_locations") or [] if isinstance(x, str)]
    places = " ".join([j.get("location") or "", where, *others])
    text = j.get("description") or ""
    if j.get("non_us"):
        verdict, note = "gap", "Outside the US."
    elif not where.strip():
        verdict, note = "partial", "The posting names no location."
    elif REMOTE.search(places) or offers(REMOTE_TEXT, text):
        verdict, note = "meets", "Remote work is offered."
    elif HYBRID.search(places) or offers(HYBRID_TEXT, text):
        verdict, note = "meets", "Hybrid: part of the week on site."
    else:
        verdict, note = "meets", "No remote or hybrid wording found."
    label = f"{where} (+{len(others)} more)" if others else where
    return _row("location", verdict, clip(label) or "Not stated", note)


def pay(j):
    """The range salary.py reads from the description. No pay target is set, so the badge only says whether one is
    stated: meets when it is, partial when it is not."""
    s = salary.extract(j.get("description") or "")
    if not s:
        return _row("pay", "partial", "Not listed", "The posting states no pay range.")
    note = "Varies by location: lowest to highest." if s["multiple"] else "Stated in the posting."
    return _row("pay", "meets", s["text"], note)


def table(j):
    """The seven rows the drawer shows: the model's four, then sponsorship, location and pay. A verdict stored before
    factors existed, an error, or no verdict at all gives [], so the page shows nothing extra."""
    v = j.get("verdict") or {}
    if not isinstance(v.get("factors"), list):
        return []
    return [dict(f, rule=False) for f in fit.model_factors(v)] + [sponsorship(j), location(j), pay(j)]
