"""Pay range from a posting's description. Workday has no structured pay field, but US pay-transparency laws put
a range in most descriptions, in many formats: "$90,000.00 - $180,000.00", "$80,750-109,250", "$118.9K - $172.2K
USD", "USD 129,400.00 To USD 207,000.00", "$21.00–$21.63" hourly. Only ranges near pay wording count."""

import re

_AMT = r"(?:USD\s*\$?\s*|US\$\s*|\$\s*)?(?:\d{1,3}(?:,\d{3})+|\d{2,7})(?:\.\d+)?(?:\s*[kK])?(?:\s*USD)?"
RANGE = re.compile(rf"(?P<a>{_AMT})\s*(?:-|–|—|to|and)\s*(?P<b>{_AMT})", re.I)
PAY_WORDS = re.compile(r"salary|pay|compensation|wage|base|hourly|annual|per (?:year|hour)|range", re.I)
SINGLE = re.compile(
    r"(?:USD\s*\$?|\$)\s?(?P<a>\d{1,3}(?:,\d{3})*(?:\.\d+)?)\s*(?:USD\s*)?(?P<per>per hour|hourly|/\s?h(?:ou)?r|per year|annually|/\s?y(?:ea)?r)",
    re.I,
)
THOUSANDS = re.compile(r"\d{2,3},\d{3}")
NOT_PAY = re.compile(r"bonus|sign-?on|relocation|tuition|reimburs|stipend|401|billion|million|revenue|assets", re.I)
# After a range only these disqualify: "includes a base salary and bonus" is still pay.
NOT_PAY_AFTER = re.compile(r"sign-?on|relocation|tuition|stipend|billion|million|revenue|assets", re.I)


def _value(s):
    s = s.upper().replace("USD", "").replace("US$", "").replace("$", "").replace(",", "").strip()
    k = s.endswith("K")
    n = float(s.rstrip("K").strip())
    return n * 1000 if k else n


def ranges(text):
    """Every plausible pay range in the text as (low, high, period)."""
    out = []
    text = text or ""
    for m in RANGE.finditer(text):
        a, b = m.group("a"), m.group("b")
        before60 = text[max(0, m.start() - 60) : m.start()]
        marked = "$" in a + b or "USD" in (a + b).upper() or "K" in (a + b).upper()
        bare_ok = THOUSANDS.search(a) and THOUSANDS.search(b) and PAY_WORDS.search(before60)
        if not marked and not bare_ok:
            continue  # two bare numbers, e.g. "2020 - 2024", unless under a pay heading like "Base Pay Range (USD)"
        # Words that make the money something else: just before the range, or on the same line just after it.
        after = text[m.end() : m.end() + 40].split("\n")[0]
        if NOT_PAY.search(before60) or NOT_PAY_AFTER.search(after):
            continue
        lo, hi = sorted((_value(a), _value(b)))
        both_dollars = "$" in a and "$" in b
        wording = PAY_WORDS.search(text[max(0, m.start() - 200) : m.start()] + text[m.end() : m.end() + 40])
        if not wording and not (both_dollars and lo >= 20_000):
            continue  # a bare range needs pay wording nearby; "$90,000 - $120,000" alone is clear enough
        if 10 <= lo and hi <= 300:
            out.append((lo, hi, "hour"))
        elif 20_000 <= lo and hi <= 1_500_000:
            out.append((lo, hi, "year"))
    if not out:  # a single stated rate, e.g. "$45 per hour", "$48.08 Hourly"
        for m in SINGLE.finditer(text):
            if NOT_PAY.search(text[max(0, m.start() - 60) : m.start()]) or not PAY_WORDS.search(
                text[max(0, m.start() - 200) : m.start()]
            ):
                continue
            v, hourly = _value(m.group("a")), "h" in m.group("per").lower()
            if hourly and 10 <= v <= 300:
                out.append((v, v, "hour"))
            elif not hourly and 20_000 <= v <= 1_500_000:
                out.append((v, v, "year"))
    return out


def extract(text):
    """{"min", "max", "period", "multiple", "text"} or None. Several ranges (by location) span their lowest to highest."""
    found = ranges(text)
    if not found:
        return None
    period = "year" if any(p == "year" for *_, p in found) else "hour"
    same = [(lo, hi) for lo, hi, p in found if p == period]
    lo, hi = min(x for x, _ in same), max(y for _, y in same)
    return {"min": lo, "max": hi, "period": period, "multiple": len(set(same)) > 1, "text": label(lo, hi, period)}


def label(lo, hi, period):
    if period == "hour":
        f = lambda v: f"${v:,.2f}".replace(".00", "")  # noqa: E731
        return f"{f(lo)}/hr" if lo == hi else f"{f(lo)} to {f(hi)}/hr"
    k = lambda v: f"${round(v / 1000):,}k"  # noqa: E731
    return k(lo) if lo == hi else f"{k(lo)} to {k(hi)}"


def sentence(text):
    """The sentence (or line) holding the first pay figure, so a page can highlight it. None when there is none."""
    if not text or not ranges(text):
        return None
    for part in re.split(r"(?<=[.!?])\s+|\n+", text):
        if ranges(part):
            return part.strip()[:300]
    return None
