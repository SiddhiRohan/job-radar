"""Sponsorship classification from posting text, with a per-company default as fallback."""
import re

# Checked in this order: a "no" phrase beats everything, then PERM-ad patterns, then "yes".
NO_PATTERNS = [
    r"no sponsorship", r"\bnot sponsor", r"\bno visa", r"unable to sponsor", r"cannot sponsor",
    r"not (?:able|willing|eligible) to sponsor",
    r"(?:does|do|will) not (?:offer|provide|support) (?:visa |immigration |employment |work )?(?:visa )?sponsorship",
    r"(?:must|should) not (?:now or in the future )?require (?:visa |immigration |employment |work )?sponsorship",
    r"without (?:the need for |requiring )?(?:visa |employer |employment |current or future )?sponsorship",
    r"\bno (?:opt|cpt)\b", r"u\.?s\.? citizens? only", r"must be (?:a |an )?u\.?s\.? citizen",
    r"citizenship (?:is )?required", r"green card (?:holders? )?or (?:u\.?s\.? )?citizen",
    r"\bitar\b", r"export control",
    r"ts/sci", r"top secret", r"secret clearance", r"\bpoly(?:graph)?\b", r"active (?:security )?clearance",
    r"(?:obtain|hold|maintain|possess)(?:ing)? (?:and maintain )?(?:a |an )?(?:[\w\-/]+ ){0,3}clearance",
    r"security clearance (?:is )?required", r"clearance (?:is )?required",
]
NO_CASE_SENSITIVE = [r"\bEAR\b"]  # export administration regulations; lowercase "ear" is a body part
PERM_PATTERNS = [
    r"\$\d{1,3}(?:,\d{3})+\.(?!00\b)\d{2}\b",  # odd-cent salary such as $128,731.21
    r"in the job offered",
    r"position requires \w+ years? (?:of experience )?in the following",
    r"the following experience is required",
    r"mail(?:ed)? (?:your |a )?r[eé]sum[eé]",
    r"refer to job code",
]
YES_PATTERNS = [
    r"sponsorship (?:is |will be )?(?:available|offered|provided|possible)",
    r"will sponsor", r"(?:able|willing|open) to sponsor", r"can sponsor", r"visa sponsorship for",
    r"\bh-?1b\b",
]


def _snippet(text, m, pad=70):
    s = text[max(0, m.start() - pad): m.end() + pad].replace("\n", " ")
    return re.sub(r"\s+", " ", s).strip()


def classify(text):
    """Return (tag, evidence) from the posting text alone: no / perm_ad / yes / unknown."""
    checks = [(NO_PATTERNS, re.I, "no"), (NO_CASE_SENSITIVE, 0, "no"),
              (PERM_PATTERNS, re.I, "perm_ad"), (YES_PATTERNS, re.I, "yes")]
    for patterns, flags, tag in checks:
        for p in patterns:
            m = re.search(p, text, flags)
            if m:
                return tag, _snippet(text, m)
    return "unknown", None


def resolve(tag, company_sponsors_h1b):
    """Posting text beats the company default. Unknown text falls back to likely/unknown/unlikely."""
    if tag != "unknown":
        return tag
    return {True: "likely", False: "unlikely"}.get(company_sponsors_h1b, "unknown")
