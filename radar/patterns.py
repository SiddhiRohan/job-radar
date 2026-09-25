"""What the rejections say. Joins applications.md with the stored postings and compares the rejection rate along a few
dimensions (title family, seniority wording, resume base, fit score, years asked, sponsorship default, company) with
the overall rate. Counts only, no model call: with a few dozen applications the honest output is "4 of 11 rejections
were Senior titles, against 20 of 98 applications", not a conclusion."""

import re
from collections import Counter, defaultdict

from radar import applications, store

FAMILIES = [
    ("Data engineer", r"data engineer|data platform|data infrastructure|\betl\b|analytics engineer"),
    ("Data scientist", r"data scien|decision scien|applied scientist"),
    ("ML engineer", r"machine learning|\bml\b|\bmle\b|deep learning|mlops"),
    ("AI engineer", r"\bai\b|artificial intelligence|gen ?ai|\bllm|\bnlp\b"),
    ("Analyst", r"analyst|analytics"),
    ("Software engineer", r"software (engineer|developer)"),
]
SENIORITY = [
    ("Senior", r"\bsenior\b|\bsr\b|\biii\b|\biv\b"),
    ("Level II", r"\bii\b|\b2\b"),
    ("Entry", r"junior|associate|\bi\b|\b1\b|new grad|early career|graduate"),
]
RESPONDED = ("screen", "interview", "offer")


def _first(rules, text, default):
    for label, rx in rules:
        if re.search(rx, text, re.I):
            return label
    return default


def dimensions(app, job):
    """The buckets one application falls into. job may be None when the posting is not stored."""
    v = (job or {}).get("verdict") or {}
    best = max([s for s in (v.get("score_entry"), v.get("score_experienced")) if isinstance(s, int)] or [0])
    years = (job or {}).get("years_required")
    return {
        "Title family": _first(FAMILIES, app["title"], "Other"),
        "Seniority in title": _first(SENIORITY, app["title"], "Unmarked"),
        "Resume base": v.get("recommended_resume") or "unknown",
        "Fit score": f"score {best}" if best else "unscored",
        "Years asked": "not stated"
        if years is None
        else "0 to 2"
        if years <= 2
        else "3 to 5"
        if years <= 5
        else "6 or more",
        "Sponsorship default": (job or {}).get("sponsorship") or "unknown",
        "Company": app["company"],
    }


def analyse(apps=None, jobs=None, min_support=3):
    """Findings per dimension: buckets with at least min_support rejections, ranked by how far their rejection rate
    sits above the overall one. Also the headline counts."""
    apps = applications.rows() if apps is None else apps
    jobs = {f"{j['company']}|{j['req_id']}": j for j in (store.load() if jobs is None else jobs)}
    total, rejected = len(apps), sum(1 for a in apps if a["status"] == "rejected")
    responded = sum(1 for a in apps if a["status"] in RESPONDED)
    tallies = defaultdict(
        lambda: defaultdict(Counter)
    )  # dimension -> bucket -> {"applied": n, "rejected": n, "responded": n}
    for a in apps:
        d = dimensions(a, jobs.get(f"{a['company']}|{a['req_id']}"))
        for dim, bucket in d.items():
            t = tallies[dim][bucket]
            t["applied"] += 1
            if a["status"] == "rejected":
                t["rejected"] += 1
            if a["status"] in RESPONDED:
                t["responded"] += 1
    overall = rejected / total if total else 0
    findings = []
    for dim, buckets in tallies.items():
        for bucket, t in buckets.items():
            if t["rejected"] < min_support:
                continue
            rate = t["rejected"] / t["applied"]
            findings.append(
                {
                    "dimension": dim,
                    "bucket": bucket,
                    "applied": t["applied"],
                    "rejected": t["rejected"],
                    "responded": t["responded"],
                    "rate": round(rate, 2),
                    "lift": round(rate - overall, 2),
                }
            )
    findings.sort(key=lambda f: (-f["lift"], -f["rejected"]))
    return {
        "total": total,
        "rejected": rejected,
        "responded": responded,
        "overall_rate": round(overall, 2),
        "enough_data": rejected >= min_support,
        "findings": findings,
        "tallies": {dim: {b: dict(t) for b, t in buckets.items()} for dim, buckets in tallies.items()},
    }


def summary(result, limit=4):
    """Plain sentences for the chat assistant and the digest."""
    if not result["enough_data"]:
        return [f"{result['rejected']} rejection(s) so far, too few to see a pattern; patterns need at least 3."]
    out = [
        f"{result['rejected']} of {result['total']} applications were rejected ({round(100 * result['overall_rate'])}%), {result['responded']} got a reply."
    ]
    for f in result["findings"][:limit]:
        if f["lift"] <= 0:
            break
        out.append(
            f"{f['dimension']}: {f['bucket']} was rejected {f['rejected']} of {f['applied']} times ({round(100 * f['rate'])}%, "
            f"{round(100 * f['lift'])} points above your overall rate)."
        )
    return out
