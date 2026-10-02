"""Numbers an agent may write: only ones that appear in what it was given. Interview prep and follow-up drafts are
read aloud or sent under the person's name, so a figure the model made up ("cut latency by 40%") is taken out and
named in a note, the way tailoring treats words outside the resume.

A figure is a token that is all number: 40, 40%, 2,000+, $120k, 1.5x, 14.2. Digits inside a name (H-1B, S3, GPT-4,
EC2), a date or range (2026-09-14, 3-5) or a ratio (1:1, 24/7) are left alone; a name is not a claim."""

import re

TOKEN = re.compile(r"[\w$.,%+:/-]+")  # 1:1, 24/7 and links stay whole
FIGURE = re.compile(r"\$?(\d+(?:,\d{3})*(?:\.\d+)?)(?:[%+xkKM]|k\+)?")
DIGITS = re.compile(r"\d+(?:,\d{3})*(?:\.\d+)?")
MISSING = "[?]"


def figure(token):
    """(core, match) when the token, less trailing punctuation, is a figure, else None."""
    core = token.rstrip(".,")
    m = FIGURE.fullmatch(core)
    return (core, m) if m else None


def norm(n):
    """One spelling per number: no thousands separators, no leading zeros, so 1,200 is 1200 and 09 is 9."""
    n = n.replace(",", "")
    return n if "." in n else str(int(n))


def numbers(text):
    """Every number in a source, inside a date or a name too: a figure may repeat any of them."""
    return {norm(n) for n in DIGITS.findall(text or "")}


def lock(value, sources, where=""):
    """value with every figure not found in sources replaced by [?], and one note per figure taken out. Walks dicts
    and lists, so a whole structured answer goes through in one call; `where` names fields in the notes."""
    allowed = numbers("\n".join(sources))
    notes = []

    def clean(v, at):
        if isinstance(v, dict):
            return {k: clean(x, f"{at}.{k}" if at else k) for k, x in v.items()}
        if isinstance(v, list):
            return [clean(x, f"{at}.{i + 1}") for i, x in enumerate(v)]
        if not isinstance(v, str):
            return v

        def swap(m):
            f = figure(m.group(0))
            if not f or norm(f[1].group(1)) in allowed:
                return m.group(0)
            core, fm = f
            notes.append(f"{fm.group(1)} in {at} is not in the posting or your resume, so it was taken out.")
            return core[: fm.start(1)] + MISSING + core[fm.end(1) :] + m.group(0)[len(core) :]

        return TOKEN.sub(swap, v)

    return clean(value, where), notes
