"""Poll verified Workday sites, apply title/location rules, enrich new postings, track them in jobs.jsonl."""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import filters
import sponsor
import wd

sys.stdout.reconfigure(encoding="utf-8")
MAX_DESC = 15000
RULES = ("seniority", "domain", "non_us", "years_gate", "sponsorship_no", "perm_ad")


def load_json(path, default):
    p = Path(path)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else default


def search_all(cfg, companies, max_days, removed):
    """Search every company x term; return (found dict keyed company|req_id, errors) after title/location rules."""
    found, errors = {}, {}
    for c in companies:
        for term in cfg["search_terms"]:
            try:
                jobs = wd.search(c["tenant"], c["shard"], c["site"], term, company=c["name"])
            except Exception as e:  # keep polling the other companies
                errors[c["name"]] = f"{term}: {str(e)[:150]}"
                print(f"  ! {c['name']} / {term}: {str(e)[:90]}", flush=True)
                break
            fresh = 0
            for j in jobs:
                key = f"{c['name']}|{j['req_id']}"
                if j["posted_days_ago"] > max_days or key in found:
                    continue
                fresh += 1
                if cfg.get("title_must_match_term", True) and not filters.title_matches_term(j["title"], term):
                    continue
                reason = filters.title_exclusion(j["title"], cfg)
                if reason:
                    removed[reason].add(key)
                elif cfg["us_only"] and (filters.looks_non_us(j["location"]) or filters.path_non_us(j["url"])):
                    removed["non_us"].add(key)
                else:
                    j["search_term"] = term
                    found[key] = j
            print(f"  {c['name']:<12} {term:<22} {len(jobs):>4} results, {fresh:>3} recent", flush=True)
    return found, errors


def enrich(j, company, cfg):
    """Fetch the detail record; derive US check, years gate, sponsorship, and contract flags."""
    d = wd.fetch_detail(company["tenant"], company["shard"], j["detail_path"])
    text = d["description"]
    j.update(description=text[:MAX_DESC], detail_location=d["location"], country=d["country"],
             additional_locations=d["additional_locations"], country_code=d["country_code"],
             time_type=d["time_type"])
    j["non_us"] = bool(cfg["us_only"] and filters.detail_non_us(d))
    j["years_required"] = filters.years_required(text)
    j["years_gate"] = j["years_required"] is not None and j["years_required"] >= 6
    tag, evidence = sponsor.classify(j["title"] + "\n" + text)
    j["sponsorship"] = sponsor.resolve(tag, company.get("sponsors_h1b"))
    j["sponsorship_evidence"] = evidence
    j["contract"], j["contract_evidence"] = filters.is_contract(j["title"], text)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, help="override max_days_ago")
    args = ap.parse_args()
    cfg = load_json("config.json", {})
    max_days = args.days if args.days is not None else cfg["max_days_ago"]
    companies = {c["name"]: c for c in load_json("companies.json", []) if c.get("verified")}
    seen = set(load_json("seen.json", []))
    removed = {r: set() for r in RULES}

    print(f"polling {len(companies)} companies x {len(cfg['search_terms'])} terms, max_days_ago={max_days}")
    found, errors = search_all(cfg, companies.values(), max_days, removed)
    new = [(k, j) for k, j in found.items() if k not in seen]
    print(f"\n{len(found)} matching postings, {len(new)} new; fetching details for the new ones", flush=True)

    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    kept = []
    for key, j in new:
        try:
            enrich(j, companies[j["company"]], cfg)
        except Exception as e:
            j["enrich_error"] = str(e)[:150]
            errors[f"{j['company']} {j['req_id']}"] = f"detail: {str(e)[:120]}"
        if j.get("non_us"):
            removed["non_us"].add(key)
            continue
        if j.get("years_gate"):
            removed["years_gate"].add(key)
        if j.get("sponsorship") == "no":
            removed["sponsorship_no"].add(key)
        elif j.get("sponsorship") == "perm_ad":
            removed["perm_ad"].add(key)
        j["first_seen"] = now
        kept.append(j)

    with open("jobs.jsonl", "a", encoding="utf-8") as f:
        for j in kept:
            f.write(json.dumps(j) + "\n")
    seen |= {k for k, _ in new}
    Path("seen.json").write_text(json.dumps(sorted(seen), indent=0), encoding="utf-8")
    Path("last_run.json").write_text(json.dumps({
        "ran_at": now, "max_days_ago": max_days, "companies_polled": len(companies),
        "new_postings": len(kept), "removed": {r: len(s) for r, s in removed.items()},
        "errors": errors}, indent=2), encoding="utf-8")

    print(f"\n{len(kept)} new postings kept; removed: " + ", ".join(f"{r}={len(s)}" for r, s in removed.items()))
    for j in sorted(kept, key=lambda j: (j["company"], j["title"])):
        flags = " ".join(f for f, on in (("YEARS", j.get("years_gate")), ("CONTRACT", j.get("contract"))) if on)
        print(f"{j['company']:<12} {j['title'][:50]:<50} {j['location'][:22]:<22} {j.get('sponsorship', '?'):<9} {flags}")


if __name__ == "__main__":
    main()
