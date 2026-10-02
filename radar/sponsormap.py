"""python -m radar.sponsormap: which employers sponsor the roles the radar finds, from what their own recent postings
say, next to each employer's default in companies.json and its H-1B filing record.

No model call. A posting says yes when its wording does (the sponsorship tag) or the model read it so, and says no
when its wording rules sponsorship out, it reads as a PERM ad, or the model read a no; a no wins, as in the digest.
Anything else is silent, and there the employer default decides. An employer whose default disagrees with its own
postings is flagged, so companies.json can be put right."""

import json
import sys
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

from radar import digest

DAYS = 60
FILINGS = Path("companies/h1b_check.json")
ORDER = ("sponsors", "mixed", "rules_out", "silent")
LABELS = {
    "sponsors": "Say they sponsor",
    "mixed": "Decide per posting",
    "rules_out": "Mostly rule it out",
    "silent": "Silent, so the default decides",
}


def reading(j):
    """What one posting itself says: "yes", "no" or "silent"."""
    tag, model = j.get("sponsorship"), (j.get("verdict") or {}).get("sponsorship")
    if tag in ("no", "perm_ad") or model in ("no", "perm_ad"):
        return "no"
    return "yes" if "yes" in (tag, model) else "silent"


def records(companies=None, filings=None):
    """{employer: {"default", "source", "filings"}} from companies.json and the filing check, for this map and for
    interview prep."""
    if companies is None:
        companies = json.loads(Path("companies.json").read_text(encoding="utf-8"))
    if filings is None:
        filings = json.loads(FILINGS.read_text(encoding="utf-8")) if FILINGS.exists() else {}
    return {
        c["name"]: {
            "default": c.get("sponsors_h1b"),
            "source": c.get("sponsorship_source") or "",
            "filings": (filings.get(c["name"]) or {}).get("fy2025"),
        }
        for c in companies
    }


def status(c):
    """Where an employer's postings put it: "mixed" when some say yes and some no, "sponsors" when the ones that say
    anything say yes, "rules_out" when most say no, else "silent"."""
    if c["yes"]:
        return "mixed" if c["no"] else "sponsors"
    return "rules_out" if c["no"] * 2 > sum(c.values()) else "silent"


def flag(c, default):
    """One sentence when the employer default and its postings disagree, else ""."""
    total = sum(c.values())
    if default is True and not c["yes"] and c["no"] >= 3 and c["no"] * 4 >= total * 3:
        return f"Its default says it sponsors, but {c['no']} of its {total} postings rule sponsorship out."
    if default is False and c["yes"]:
        return f"Its default says it does not sponsor, but {c['yes']} of its postings say it does."
    if default is None and c["yes"]:
        return f"It has no default yet, and {c['yes']} of its postings say it sponsors."
    return ""


def analyse(jobs=None, recs=None, days=DAYS, today=None):
    """Employers with a posting first seen in the last `days`, grouped by what their postings say, most yeses first."""
    jobs = digest.load_jsonl("jobs.jsonl") if jobs is None else jobs
    recs = records() if recs is None else recs
    since = ((today or datetime.now()) - timedelta(days=days)).strftime("%Y-%m-%d")
    seen = {}
    for j in jobs:
        if (j.get("first_seen") or "")[:10] >= since:
            seen.setdefault(j["company"], Counter())[reading(j)] += 1
    out = []
    for name, c in seen.items():
        rec = recs.get(name) or {"default": None, "source": "", "filings": None}
        out.append(
            {"company": name, "postings": sum(c.values()), "yes": c["yes"], "no": c["no"], "silent": c["silent"]}
            | {"status": status(c), "flag": flag(c, rec["default"])}
            | rec
        )
    out.sort(key=lambda e: (ORDER.index(e["status"]), -e["yes"], -e["postings"], e["company"]))
    return {
        "since": since,
        "days": days,
        "counts": {s: sum(e["status"] == s for e in out) for s in ORDER},
        "employers": out,
        "flags": [e for e in out if e["flag"]],
    }


def summary(result, limit=8):
    """Plain lines for the terminal, the assistant and the brief."""
    if not result["employers"]:
        return [f"No postings since {result['since']} to read sponsorship from yet."]
    yes = sorted((e for e in result["employers"] if e["yes"]), key=lambda e: (-e["yes"], e["company"]))
    n = result["counts"]
    lines = [
        f"Since {result['since']}, {len(result['employers'])} employers posted: {n['sponsors']} say they sponsor, "
        f"{n['mixed']} decide per posting, {n['rules_out']} mostly rule it out, and {n['silent']} never say."
    ]
    if yes:
        most = ", ".join(f"{e['company']} ({e['yes']} of {e['postings']})" for e in yes[:limit])
        lines.append(f"Most postings that say they sponsor: {most}.")
    lines += [f"Check {e['company']}: {e['flag']}" for e in result["flags"][:limit]]
    return lines


def default_label(d):
    return {True: "likely", False: "unlikely"}.get(d, "unknown")


def main():
    r = analyse()
    print("\n".join(summary(r)))
    for s in ORDER:
        group = [e for e in r["employers"] if e["status"] == s]
        print(f"\n{LABELS[s]} ({len(group)})")
        for e in group:
            extra = f" | filings {e['filings']}" if e["filings"] else ""
            print(
                f"  {e['company']}: {e['yes']} yes, {e['no']} no, {e['silent']} silent | default "
                f"{default_label(e['default'])}{extra}"
            )


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
