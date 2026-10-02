"""Numbers an agent may write: only ones that appear in what it was given. Interview prep and follow-up drafts are
read aloud or sent under the person's name, so a figure the model made up ("cut latency by 40%") is taken out and
named in a note, the way tailoring treats words outside the resume.

Every number counts, whatever its units: 40%, 800ms, $2B, 12-person, 2019-2021. Digits that are part of a name
(H-1B, S3, GPT-4, Neo4j) or a ratio (1:1, 24/7) are not figures and are left as written."""

import re

RUN = re.compile(r"\d+(?:,\d{3})*(?:\.\d+)?")
MISSING = "[?]"


def norm(n):
    """One spelling per number: no thousands separators, no leading zeros, so 1,200 is 1200 and 09 is 9."""
    n = n.replace(",", "")
    return n if "." in n else str(int(n))


def numbers(text):
    """Every number in a source, inside a date or a name too: a figure may repeat any of them."""
    return {norm(n) for n in RUN.findall(text or "")}


def named(text, start, end):
    """The digits at text[start:end] belong to a name or a ratio: a letter right before them (S3, EC2, Neo4j), a
    letter and a hyphen (H-1B, GPT-4), or digits on the far side of a colon or slash (1:1, 24/7)."""
    before, after = text[max(0, start - 2) : start], text[end : end + 2]
    if before[-1:].isalpha() or (before[-1:] == "-" and before[:1].isalpha()):
        return True
    return (before[-1:] in ":/" and before[:1].isdigit()) or (after[:1] in ":/" and after[1:2].isdigit())


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
        out, last = [], 0
        for m in RUN.finditer(v):
            if named(v, m.start(), m.end()) or norm(m.group(0)) in allowed:
                continue
            notes.append(f"{m.group(0)} in {at} is not in the posting or your resume, so it was taken out.")
            out += [v[last : m.start()], MISSING]
            last = m.end()
        return "".join(out) + v[last:]

    return clean(value, where), notes
