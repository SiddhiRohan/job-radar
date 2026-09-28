"""What score.py asks the model for, and the fit it returns factor by factor: experience, level, skills and domain,
each with a verdict and short evidence from the posting and the resume. Verdicts stored before factors existed have
none; model_factors() reads them back as [] and drops malformed entries, so nothing downstream needs a guard."""

MODEL_FACTORS = ("experience", "level", "skills", "domain")
VERDICTS = ("meets", "partial", "gap")
FIELDS = ("factor", "verdict", "posting", "resume", "note")

RULES = """You are a blunt technical recruiter screening one candidate against one job posting.
Score each resume base 1-5: 5 = clearly meets every must-have; 4 = meets must-haves with minor gaps;
3 = plausible with a tailored resume; 2 = significant gaps; 1 = don't bother. No flattery.
recommended_resume: entry for New College Grad, junior, I-level, 0-2 years, or associate roles;
experienced for 3+ years, II/mid, or senior roles. recommended_variant is "<role folder>/<one-page|two-page>"
using only the role folders listed. years_required: the minimum years the posting demands, or null.
platform_tools_missing: only tools from the profile's NOT-have list that the posting requires.
sponsorship: from the posting text only (no/yes/perm_ad/unknown); sponsorship_evidence quotes the phrase or is null.
cover_letter_required: true only if the posting asks for one. why: two sentences max.
factors come first: exactly four, in this order, each judged against the better-fitting resume base.
experience = years and depth in the same kind of work the role needs, not keyword overlap; level = seniority fit;
skills = the must-have skills the resume proves (if one is missing, note is "Missing: <the most important one>.");
domain = familiarity with the industry or problem area. verdict: meets, partial or gap. posting: what the posting
asks, quoted or paraphrased, 20 words max. resume: the matching evidence from that resume, 20 words max, or "".
note: one short sentence, or "". The scores and why must agree with the factors."""

FACTOR = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "factor": {"type": "string", "enum": list(MODEL_FACTORS)},
        "verdict": {"type": "string", "enum": list(VERDICTS)},
        "posting": {"type": "string"},
        "resume": {"type": "string"},
        "note": {"type": "string"},
    },
    "required": list(FIELDS),
}
# Factors first, so the scores are written after the evidence. No minimum/maximum or length keywords anywhere: the
# structured-output endpoint rejects them with a 400, so counts and lengths are asked for in RULES instead.
PROPERTIES = {
    "factors": {"type": "array", "items": FACTOR},
    "score_entry": {"type": "integer", "enum": [1, 2, 3, 4, 5]},
    "score_experienced": {"type": "integer", "enum": [1, 2, 3, 4, 5]},
    "recommended_resume": {"type": "string", "enum": ["entry", "experienced"]},
    "recommended_variant": {"type": "string"},
    "years_required": {"type": ["integer", "null"]},
    "hard_requirements_missing": {"type": "array", "items": {"type": "string"}},
    "platform_tools_missing": {"type": "array", "items": {"type": "string"}},
    "sponsorship": {"type": "string", "enum": ["yes", "likely", "unknown", "unlikely", "no", "perm_ad"]},
    "sponsorship_evidence": {"type": ["string", "null"]},
    "cover_letter_required": {"type": "boolean"},
    "why": {"type": "string"},
    "apply": {"type": "boolean"},
}
SCHEMA = {"type": "object", "additionalProperties": False, "properties": PROPERTIES, "required": list(PROPERTIES)}


def model_factors(verdict):
    """The model's factors in the order of MODEL_FACTORS, one per name, every field a string. An old verdict, a rule
    verdict or an error gives []; an entry with an unknown name or verdict is dropped rather than shown."""
    raw = (verdict or {}).get("factors")
    found = {}
    for f in raw if isinstance(raw, list) else []:
        if isinstance(f, dict) and f.get("factor") in MODEL_FACTORS and f.get("verdict") in VERDICTS:
            found.setdefault(f["factor"], {k: str(f.get(k) or "") for k in FIELDS})
    return [found[name] for name in MODEL_FACTORS if name in found]
