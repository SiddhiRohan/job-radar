"""Write COMPANIES_REPORT.md from candidates.json, companies.json, and not_on_workday.json; estimate daily run time."""

import json
from collections import Counter

SEC_PER_PAGE = 1.6  # measured: 1122 pages in 30 min on the 2026-09-13 run (1.5 s gap, cache hits are free)


def main():
    cands = json.load(open("candidates.json", encoding="utf-8"))
    companies = json.load(open("companies.json", encoding="utf-8"))
    not_wd = json.load(open("not_on_workday.json", encoding="utf-8"))
    cfg = json.load(open("config.json", encoding="utf-8"))
    pages = {int(k): v for k, v in cfg.get("max_pages_by_tier", {}).items()}
    terms = len(cfg["search_terms"])
    status = Counter(e.get("status") for e in cands.values())
    seeded = 15  # verified before this expansion

    def minutes(tiers):
        return (
            sum(
                (terms + len(c.get("extra_terms") or [])) * pages.get(c["tier"], 10) * SEC_PER_PAGE
                for c in companies
                if c["tier"] in tiers
            )
            / 60
        )

    daily, tier3 = minutes({1, 2}), minutes({3})
    ats = Counter((v.get("ats") or "unknown").split(" ")[0].split("(")[0].rstrip(";,") for v in not_wd.values())
    md = [
        "# Companies report (2026-09-13)",
        "",
        f"- Candidates considered: {len(cands) + seeded} ({seeded} already verified before this pass, {len(cands)} new names)",
        f"- Resolved to a Workday slug from search-result URLs: {status['verified'] + status['failed']}",
        f"- Verified (empty search returned `total`): {status['verified']} new, {len(companies)} total in companies.json",
        f"- Failed verification twice and dropped: {status['failed']}",
        f"- Not on Workday: {len(not_wd)} (see `not_on_workday.json`; {sum(1 for v in not_wd.values() if v.get('second_search'))} of "
        "them got only one search because the session's web-search budget ran out)",
        "",
        "## Not on Workday, by ATS seen",
        "",
    ]
    md += [f"- {k}: {v}" for k, v in ats.most_common()]
    md += [
        "",
        "## Estimated run time",
        "",
        f"- Per search: pages x {SEC_PER_PAGE:.1f} s; pages per tier: {pages}; {terms} search terms per company",
        f"- Daily (tier 1 + 2, {sum(c['tier'] <= 2 for c in companies)} companies): about {daily:.0f} min for the search phase, "
        "plus roughly 2 s per new posting for detail fetches and 8 s per scored posting",
        f"- Tier 3 days (Mon/Thu, +{sum(c['tier'] == 3 for c in companies)} companies): about {daily + tier3:.0f} min",
        "- Cache hits (same day reruns) cost nothing.",
        "",
    ]
    for t in (1, 2, 3):
        rows = [c for c in companies if c["tier"] == t]
        md += [
            f"## Tier {t} ({len(rows)})",
            "",
            "| Company | Tenant | Site | Open roles | sponsors_h1b | Source |",
            "|---|---|---|---|---|---|",
        ]
        md += [
            f"| {c['name']} | {c['tenant']}.{c['shard']} | {c['site']} | {c.get('open_roles', '')} | {c['sponsors_h1b']} | "
            f"{c['sponsorship_source']} |"
            for c in rows
        ]
        md.append("")
    open("COMPANIES_REPORT.md", "w", encoding="utf-8").write("\n".join(md))
    print(f"daily ~{daily:.0f} min, tier-3 days ~{daily + tier3:.0f} min; {len(companies)} companies")


if __name__ == "__main__":
    main()
