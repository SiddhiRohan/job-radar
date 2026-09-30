"""Build digests/YYYY-MM-DD.md from this run's new postings: Apply, Maybe, Contract, counts, Skipped, Errors."""

import json
import sys
from datetime import datetime
from pathlib import Path

from radar import filters, fit, salary, store

sys.stdout.reconfigure(encoding="utf-8")


def load_jsonl(path):
    """One row per posting even if an older file holds duplicates from overlapping runs."""
    p = Path(path)
    rows = (
        [json.loads(line) for line in p.read_text(encoding="utf-8").splitlines() if line.strip()] if p.exists() else []
    )
    return store.dedupe(rows)


def best(j):
    v = j.get("verdict") or {}
    scores = [v.get("score_entry"), v.get("score_experienced")]
    return max(s for s in scores if isinstance(s, int)) if any(isinstance(s, int) for s in scores) else 0


def line(j, gaps=False):
    """One posting; with gaps, a line naming the factors that are partial or a gap (none for older verdicts)."""
    v = j.get("verdict") or {}
    pair = f"E{v.get('score_entry', '-')}/X{v.get('score_experienced', '-')}"
    rec = f"{v.get('recommended_resume') or '?'} · {v.get('recommended_variant') or '?'}"
    cover = " · [COVER LETTER]" if v.get("cover_letter_required") else ""
    pay = (salary.extract(j.get("description", "")) or {}).get("text", "pay not listed")
    out = [
        f"- **{j['company']}** | {j['title']} | {j.get('detail_location') or j['location']} | {j['posted_on']} | "
        f"{pair} | {pay} | {rec}{cover} | [link]({j['url']})"
    ]
    if v.get("why"):
        out.append(f"    {v['why']}")
    if gaps and (gap := fit.gap_line(v)):
        out.append(f"    {gap}")
    extras = []
    if v.get("hard_requirements_missing"):
        extras.append("missing: " + ", ".join(v["hard_requirements_missing"]))
    if v.get("platform_tools_missing"):
        extras.append("platform tools: " + ", ".join(v["platform_tools_missing"]))
    if j.get("contract"):
        extras.append(f"contract evidence: {j.get('contract_evidence')}")
    out += [f"    {e}" for e in extras]
    return "\n".join(out)


def section(title, items, gaps=False):
    if not items:
        return [f"## {title} (0)", ""]
    return (
        [f"## {title} ({len(items)})", ""]
        + [line(j, gaps) for j in sorted(items, key=lambda j: (-best(j), j["company"], j["title"]))]
        + [""]
    )


def model_says(j):
    return (j.get("verdict") or {}).get("sponsorship")


def says_no(j):
    """The posting text says no (regex tag or the model's read). A negative company default alone ("unlikely") also
    skips, unless the model read the posting as sponsoring: some employers decide per posting (Capital One)."""
    if j.get("sponsorship") in ("no", "perm_ad") or model_says(j) == "no":
        return True
    return j.get("sponsorship") == "unlikely" and model_says(j) != "yes"


def sponsors(j):
    """Good enough for Apply: the text or company default says yes, or the model read the posting as sponsoring."""
    return j.get("sponsorship") in ("yes", "likely") or model_says(j) == "yes"


def sections(new):
    """Split one run's postings into apply / entry / maybe / contract / lower / skipped. Shared with the web UI."""
    skipped = [j for j in new if says_no(j)]
    contract = [j for j in new if j.get("contract") and j not in skipped]
    pool = [j for j in new if j not in skipped and j not in contract and not j.get("years_gate")]
    apply_ = [j for j in pool if sponsors(j) and best(j) >= 4]
    maybe = [j for j in pool if not sponsors(j) and best(j) >= 4]
    # Junior and new-grad roles rarely score 4: the model marks them down for being a narrow or generic fit.
    # They are still the right roles to apply to, so they get their own section instead of the collapsed tail.
    entry = [
        j for j in pool if j not in apply_ and j not in maybe and best(j) >= 3 and filters.is_entry_title(j["title"])
    ]
    seen = skipped + contract + apply_ + maybe + entry
    lower = [j for j in new if j not in seen]
    return {"apply": apply_, "entry": entry, "maybe": maybe, "contract": contract, "lower": lower, "skipped": skipped}


def build(run, jobs):
    # By date, not by the exact run timestamp: a second run on the same day would otherwise report an empty digest.
    today = (run.get("ran_at") or "")[:10] or datetime.now().strftime("%Y-%m-%d")
    new = [j for j in jobs if j.get("first_seen", "")[:10] == today]
    removed = run.get("removed") or {}
    md = [
        f"# Job radar digest {today}",
        "",
        f"Companies polled: {run.get('companies_polled', 0)} | Window: last {run.get('max_days_ago', '?')} day(s) | "
        f"New postings kept: {len(new)}",
        "Removed by rule: " + ", ".join(f"{k} {v}" for k, v in removed.items()),
        "",
    ]
    s = sections(new)
    skipped, contract, apply_, maybe = s["skipped"], s["contract"], s["apply"], s["maybe"]
    md += (
        section("Apply", apply_, gaps=True)
        + section("Entry level", s["entry"], gaps=True)
        + section("Maybe", maybe)
        + section("Contract / backup", contract)
    )

    lower = [j for j in s["lower"] if not j.get("years_gate")]
    counts = {s: sum(best(j) == s for j in lower) for s in (3, 2, 1)}
    unscored = sum(best(j) == 0 for j in lower)
    gated = sum(bool(j.get("years_gate")) for j in new if j not in skipped)
    md += [
        "## Lower scores (collapsed)",
        "",
        f"- score 3: {counts[3]} | score 2: {counts[2]} | score 1: {counts[1]} (years gate {gated}) | unscored: {unscored}",
        "",
    ]

    md += [f"## Skipped: sponsorship no / clearance / PERM ad ({len(skipped)})", ""]
    for j in sorted(skipped, key=lambda j: (j["sponsorship"], j["company"], j["title"])):
        v = j.get("verdict") or {}
        tag = j["sponsorship"] if j["sponsorship"] in ("no", "perm_ad", "unlikely") else f"model:{v.get('sponsorship')}"
        ev = j.get("sponsorship_evidence") or v.get("sponsorship_evidence") or "company default sponsors_h1b=false"
        md.append(f'- {tag} | **{j["company"]}** | {j["title"]} | "{ev[:160]}" | [link]({j["url"]})')
    md.append("")

    errors = dict(run.get("errors") or {})
    errors.update(
        {
            f"{j['company']} {j['req_id']}": f"score: {j['verdict']['error'][:100]}"
            for j in new
            if "error" in (j.get("verdict") or {})
        }
    )
    md += ["## Errors", ""] + ([f"- {k}: {v}" for k, v in errors.items()] or ["- none"])
    return today, "\n".join(md) + "\n"


def main():
    run = json.loads(Path("last_run.json").read_text(encoding="utf-8")) if Path("last_run.json").exists() else {}
    today, md = build(run, load_jsonl("jobs.jsonl"))
    Path("digests").mkdir(exist_ok=True)
    out = Path("digests") / f"{today}.md"
    out.write_text(md, encoding="utf-8")
    print(md)
    print(f"(written to {out})")


if __name__ == "__main__":
    main()
