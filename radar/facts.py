"""Numbers an agent may write: only ones that appear in what it was given. Interview prep and follow-up drafts are
read aloud or sent under the person's name, so a figure the model made up ("cut latency by 40%") is taken out and
named in a note, the way tailoring treats words outside the resume."""

import re

NUMBER = re.compile(r"\d+(?:,\d{3})*(?:\.\d+)?")
MISSING = "[?]"


def numbers(text):
    """The numbers in a text, with thousands separators dropped: "1,200 users" and "1200" are the same number."""
    return {n.replace(",", "") for n in NUMBER.findall(text or "")}


def lock(value, sources, where=""):
    """value with every number not found in sources replaced by [?], and one note per number taken out. Walks dicts
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
            if m.group(0).replace(",", "") in allowed:
                return m.group(0)
            notes.append(f"{m.group(0)} in {at} is not in the posting or your resume, so it was taken out.")
            return MISSING

        return NUMBER.sub(swap, v)

    return clean(value, where), notes
