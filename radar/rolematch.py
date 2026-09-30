"""Which application a rejection email is about, from the role it names. Pure functions.

Rejection emails rarely carry the requisition id, but nearly all name the role: "applying for the Data Engineer II
position", "the position of Machine Learning Engineer at Northwind". Calibrated on a set of real rejection emails
that carried no requisition id: every one named the role. Only the subject and the start of the body are
read, because footers often list other openings ("jobs you may like") whose titles would match by accident."""

import re

HEAD = 1500  # characters of body read; the role is named in the opening lines
# A title found right after one of these words, or right before a level, is a different, longer title:
# "Data Scientist" inside "Senior Data Scientist" or "Data Scientist I - Card Fraud".
QUALIFIERS = {"senior", "sr", "lead", "principal", "staff", "associate", "junior", "jr", "head", "chief", "intern"}
LEVEL = re.compile(r"^(?:i{1,3}|iv|v|[1-5])$")
# Phrases that introduce the role. The capture must start with a capital or a digit, as a title does.
ROLE = [
    re.compile(
        r"(?i:\b(?:for|to|in)\s+(?:the\s+|our\s+)?)([A-Z0-9(][^\n]{2,120}?)\s+(?i:position|role|opening|job|vacancy)\b"
    ),
    re.compile(r"(?i:\bposition of\s+)([A-Z0-9(][^\n]{2,120}?)\s+(?i:at|with)\b"),
    re.compile(r"(?i:following position:\s*)([A-Z0-9(][^\n]{2,120}?)(?:\s{2,}| We\b|\.)"),
]
NOT_A_TITLE = {"you", "your", "we", "our", "us", "the", "this", "that", "time", "effort", "application", "applying"}


def head(subject, body):
    return re.sub(r"\s+", " ", f"{subject or ''}\n{(body or '')[:HEAD]}".replace("’", "'"))


def words(s):
    return re.findall(r"[a-z0-9]+", (s or "").lower())


def title_words(title):
    """Words of a stored title, without a leading tag such as "(USA)" that the email itself leaves out."""
    return words(re.sub(r"^\s*\([^)]*\)\s*", "", title or ""))


def _names(seq, toks):
    """True when seq appears in toks as a whole title: not after a seniority word, not before a level."""
    n = len(seq)
    for i in range(len(toks) - n + 1):
        if toks[i : i + n] == seq:
            before = toks[i - 1] if i else ""
            after = toks[i + n] if i + n < len(toks) else ""
            if before not in QUALIFIERS and not LEVEL.match(after):
                return True
    return False


def by_title(text, apps):
    """Applications whose title the text names. Titles of one word are too loose and never match. When one hit's
    title is part of another's ("Data Engineer" and "Senior Data Engineer"), only the longer one counts."""
    toks = words(text)
    hits = [(a, seq) for a in apps if len(seq := title_words(a.get("title"))) >= 2 and _names(seq, toks)]

    def inside(short, long):
        return len(short) < len(long) and any(long[i : i + len(short)] == short for i in range(len(long)))

    return [a for a, seq in hits if not any(inside(seq, other) for _, other in hits)]


def named_role(text):
    """The role an email names, as written, or None. Used to tell "a role not on your list" from "no role named"."""
    text = text or ""
    for rx in ROLE:
        pos = 0
        # Search again from just past each false start: "in Walmart. We appreciate ... apply for the (USA) Data
        # Scientist III position" first matches from "in", and a non-overlapping scan would skip the real phrase.
        while m := rx.search(text, pos):
            role = m.group(1).strip(" ,.-")
            if role and ". " not in role and not NOT_A_TITLE & set(words(role)):
                return role
            pos = m.start() + 1
    return None
