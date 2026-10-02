"""python -m radar.gaps: the skills scored postings keep finding missing, counted over the last 30 days.

Three sources, all already in each verdict, so no model call: the skills factor's "Missing: ..." note, the hard
requirements the model found missing, and the tools from the profile's not-have list that the posting needs. A skill
counts once per posting, with how many of those postings scored 3, one short of Apply, so the list leads with what
would move the most postings. A skill already in skills_confirmed.md is shown apart: the postings could not see it on
the resume, so the fix is the resume rather than a course."""

import re
import sys
from collections import defaultdict
from datetime import datetime, timedelta

from radar import digest, fit
from tailoring import skills

DAYS = 30
CUT = re.compile(r"\(.*?(?:\)|$)|\[.*?(?:\]|$)")  # parentheses hold commentary, not skill names
SENTENCE = re.compile(r"[;:]|\s[-–—]\s|\.(?:\s|$)")
SPLIT = re.compile(r"\s*(?:/|,|&|\band\b|\bor\b)\s*", re.I)
FILLER = re.compile(
    r"^(?:explicit|dedicated|formal|demonstrated|foundational|hands-on|strong|proven|solid|deep|large-scale|"
    r"production-scale|production-grade)\s+",
    re.I,
)
TAIL = re.compile(
    r"\s+(?:experience|skills?|expertise|knowledge|familiarity|proficiency|background|exposure|programming|at depth|"
    r"at (?:\S+ )?scale)$",
    re.I,
)
VAGUE = re.compile(
    r"^(?:equivalent|similar|other|related|any|etc|both|which|that|the|an?|is|are|with)\b|\byears?\b|\d", re.I
)
ALIASES = {
    "google cloud": "gcp",
    "google cloud platform": "gcp",
    "amazon web services": "aws",
    "microsoft azure": "azure",
    "k8s": "kubernetes",
    "powerbi": "power bi",
}
GENERIC = {"ai", "ml", "llm", "llms", "api", "apis", "data", "cloud", "analytics", "software", "engineering"}


def terms(text):
    """Short skill names in one missing-item text: "GCP/BigQuery (required, ...)" gives GCP and BigQuery. Only the
    first clause counts, and a phrase of more than three words is a description, not a skill name."""
    first = SENTENCE.split(CUT.sub(" ", text or ""), maxsplit=1)[0]
    out = []
    for part in SPLIT.split(first):
        part = TAIL.sub("", FILLER.sub("", part.strip(" .'\"")))
        if part and not VAGUE.search(part) and len(part.split()) <= 3 and len(part) <= 30:
            out.append(part)
    return out


def key(name):
    k = " ".join(name.lower().split())
    return ALIASES.get(k, k)


def missing(verdict):
    """Every missing skill one verdict names, as (name, from the not-have list)."""
    out = []
    for f in fit.model_factors(verdict):
        m = re.search(r"missing:?\s*(.*)", f["note"], re.I) if f["factor"] == "skills" else None
        out += [(t, False) for t in terms(m.group(1))] if m and f["verdict"] != "meets" else []
    for item in verdict.get("hard_requirements_missing") or []:
        out += [(t, False) for t in terms(item)]
    for item in verdict.get("platform_tools_missing") or []:
        out += [(t, True) for t in terms(item)]
    return out


def analyse(jobs=None, confirmed=None, days=DAYS, today=None, min_postings=2):
    """Skills missing from at least `min_postings` postings scored since the window began, most near misses first."""
    jobs = digest.load_jsonl("jobs.jsonl") if jobs is None else jobs
    confirmed = {key(s) for s in (skills.load() if confirmed is None else confirmed)}
    since = ((today or datetime.now()) - timedelta(days=days)).strftime("%Y-%m-%d")
    scored = [j for j in jobs if (j.get("first_seen") or "")[:10] >= since and digest.best(j)]
    seen = defaultdict(lambda: {"names": defaultdict(int), "postings": [], "not_have": False})
    for j in scored:
        found = {}
        for name, not_have in missing(j.get("verdict") or {}):
            found.setdefault(key(name), []).append((name, not_have))
        for k, hits in found.items():
            if k in GENERIC:  # too broad to learn or to show: every posting in these roles mentions them
                continue
            s = seen[k]
            s["names"][hits[0][0]] += 1
            s["postings"].append(j)
            s["not_have"] |= any(nh for _, nh in hits)
    out = []
    for k, s in seen.items():
        if len(s["postings"]) < min_postings:
            continue
        ranked = sorted(s["postings"], key=lambda j: (digest.best(j) != 3, -digest.best(j)))
        out.append(
            {
                "skill": max(s["names"], key=s["names"].get),
                "postings": len(s["postings"]),
                "scored_3": sum(digest.best(j) == 3 for j in s["postings"]),
                "scored_4": sum(digest.best(j) >= 4 for j in s["postings"]),
                "not_have": s["not_have"],
                "confirmed": k in confirmed,
                "examples": [
                    {k2: j.get(k2, "") for k2 in ("company", "title", "req_id", "url")} | {"score": digest.best(j)}
                    for j in ranked[:3]
                ],
            }
        )
    out.sort(key=lambda g: (-g["scored_3"], -g["postings"], g["skill"].lower()))
    return {"since": since, "postings": len(scored), "skills": out, "confirmed": [g for g in out if g["confirmed"]]}


def summary(result, limit=5):
    """Plain lines for the terminal, the assistant and the brief."""
    if not result["skills"]:
        return [
            f"No skill is missing from two or more of the {result['postings']} postings scored since {result['since']}."
        ]
    lines = [f"Across {result['postings']} postings scored since {result['since']}, the skills most often missing:"]
    for g in [g for g in result["skills"] if not g["confirmed"]][:limit]:
        note = "; it is on your not-have list" if g["not_have"] else ""
        lines.append(
            f"{g['skill']}: missing in {g['postings']} postings; {g['scored_3']} of them scored 3, one point below "
            f"Apply{note}."
        )
    for g in result["confirmed"][:limit]:
        lines.append(
            f"You confirmed {g['skill']}, yet {g['postings']} postings could not find it: show it on your resume."
        )
    return lines


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    print("\n".join(summary(analyse(), limit=12)))
