"""Poll verified Workday sites for recent postings; track new ones in jobs.jsonl / seen.json."""
import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import wd

sys.stdout.reconfigure(encoding="utf-8")

NON_US = [
    "canada", "mexico", "brazil", "argentina", "colombia", "chile", "united kingdom", "uk", "england",
    "london", "ireland", "dublin", "germany", "france", "paris", "spain", "italy", "netherlands", "amsterdam",
    "poland", "warsaw", "czech", "prague", "romania", "sweden", "stockholm", "denmark", "finland", "norway",
    "switzerland", "zurich", "austria", "belgium", "portugal", "lisbon", "hungary", "israel", "tel aviv",
    "india", "bangalore", "bengaluru", "hyderabad", "pune", "chennai", "mumbai", "gurgaon", "gurugram",
    "noida", "delhi", "china", "shanghai", "beijing", "shenzhen", "taiwan", "taipei", "hsinchu", "japan",
    "tokyo", "korea", "seoul", "singapore", "malaysia", "kuala lumpur", "philippines", "manila", "vietnam",
    "thailand", "bangkok", "indonesia", "jakarta", "australia", "sydney", "melbourne", "new zealand",
    "hong kong", "dubai", "uae", "saudi", "riyadh", "egypt", "south africa", "nigeria", "kenya", "turkey",
    "costa rica", "guatemala", "puerto rico", "bermuda", "toronto", "vancouver", "montreal", "ottawa",
    "calgary", "munich", "berlin", "madrid", "barcelona", "milan", "krakow", "cambridge, uk", "reading, uk",
]


def looks_non_us(location):
    s = location.lower()
    if re.search(r"\b(us|usa|united states|u\.s\.)\b", s):
        return False
    return any(re.search(r"\b" + re.escape(w) + r"\b", s) for w in NON_US)


def title_ok(title, cfg):
    t = title.lower()
    if any(re.search(r"\b" + re.escape(w.lower()) + r"\b", t) for w in cfg["exclude_title_words"]):
        return False
    inc = cfg.get("include_title_words") or []
    return not inc or any(w.lower() in t for w in inc)


def title_matches_term(title, term):
    """Some tenants (Salesforce) do keyword-OR search; require a term word in the title.
    Short words (ai, ml) must match whole; longer ones may match as substrings (grad/graduate)."""
    t = title.lower()
    for w in term.lower().split():
        if len(w) <= 3 and re.search(r"\b" + re.escape(w) + r"\b", t):
            return True
        if len(w) > 3 and w in t:
            return True
    return False


def load_json(path, default):
    p = Path(path)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else default


def poll(max_days_ago, cfg, companies):
    """Return (kept postings dict keyed by company|req_id, errors dict)."""
    found, errors = {}, {}
    for c in companies:
        for term in cfg["search_terms"]:
            try:
                jobs = wd.search(c["tenant"], c["shard"], c["site"], term, company=c["name"])
            except Exception as e:  # keep polling other companies
                errors[c["name"]] = f"{term}: {e}"
                print(f"  ! {c['name']} / {term}: {str(e)[:90]}", flush=True)
                break
            fresh = [j for j in jobs if j["posted_days_ago"] <= max_days_ago]
            for j in fresh:
                key = f"{c['name']}|{j['req_id']}"
                if key not in found and title_ok(j["title"], cfg) \
                        and (not cfg.get("title_must_match_term", True) or title_matches_term(j["title"], term)) \
                        and not (cfg["us_only"] and looks_non_us(j["location"])):
                    j["search_term"] = term
                    found[key] = j
            print(f"  {c['name']:<12} {term:<22} {len(jobs):>4} results, {len(fresh):>3} recent", flush=True)
    return found, errors


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, help="override max_days_ago")
    args = ap.parse_args()
    cfg = load_json("config.json", {})
    max_days = args.days if args.days is not None else cfg["max_days_ago"]
    companies = [c for c in load_json("companies.json", []) if c.get("verified")]
    seen = set(load_json("seen.json", []))

    print(f"polling {len(companies)} companies x {len(cfg['search_terms'])} terms, max_days_ago={max_days}")
    found, errors = poll(max_days, cfg, companies)
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    new = [dict(j, first_seen=now) for k, j in found.items() if k not in seen]

    with open("jobs.jsonl", "a", encoding="utf-8") as f:
        for j in new:
            f.write(json.dumps(j) + "\n")
    seen |= {f"{j['company']}|{j['req_id']}" for j in new}
    Path("seen.json").write_text(json.dumps(sorted(seen), indent=0), encoding="utf-8")
    Path("last_run.json").write_text(json.dumps({
        "ran_at": now, "max_days_ago": max_days, "companies_polled": len(companies),
        "new_postings": len(new), "errors": errors}, indent=2), encoding="utf-8")

    print(f"\n{len(found)} matching postings, {len(new)} new\n")
    for j in sorted(new, key=lambda j: (j["company"], j["title"])):
        print(f"{j['company']:<12} {j['title'][:55]:<55} {j['location'][:28]:<28} {j['posted_on']}")


if __name__ == "__main__":
    main()
