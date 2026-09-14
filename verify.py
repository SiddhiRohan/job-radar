"""Verify companies.json entries against Workday; fix site slugs via tenant-root redirect."""

import json
import re
import sys
from datetime import datetime, timezone

import requests

import wd

sys.stdout.reconfigure(encoding="utf-8")


def discover_site(tenant, shard):
    """Hit the tenant root and follow redirects; return the site slug from the final URL."""
    headers = dict(wd.HEADERS, Accept="text/html,*/*")
    r = requests.get(wd.base_url(tenant, shard), headers=headers, timeout=30, allow_redirects=True)
    m = re.search(r"myworkdayjobs\.com/(?:[a-z]{2}-[A-Z]{2}/)?([^/?#]+)", r.url)
    return m.group(1) if m and m.group(1) != "wday" else None


def verify_one(c):
    """Return (ok, total_or_error). Mutates c['site'] if a redirect finds a better slug."""
    try:
        return True, wd.count(c["tenant"], c["shard"], c["site"])
    except (requests.HTTPError, ValueError, json.JSONDecodeError) as first_err:
        try:
            site = discover_site(c["tenant"], c["shard"])
        except requests.RequestException as e:
            return False, f"{first_err}; root fetch failed: {e}"
        if not site or site == c["site"]:
            return False, str(first_err)
        try:
            total = wd.count(c["tenant"], c["shard"], site)
            c["site"] = site
            return True, total
        except (requests.HTTPError, ValueError, json.JSONDecodeError) as e:
            return False, f"{first_err}; retry with site={site}: {e}"
    except requests.RequestException as e:
        return False, str(e)


def main():
    companies = json.load(open("companies.json", encoding="utf-8"))
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    rows = []
    for c in companies:
        if not (c.get("tenant") and c.get("shard") and c.get("site")):
            rows.append((c["name"], "SKIP", c.get("todo", "missing tenant/shard/site")))
            continue
        ok, result = verify_one(c)
        c["verified"] = ok
        c["verified_at"] = now
        if ok:
            c["open_roles"] = result
            c.pop("error", None)
            c.pop("todo", None)
            rows.append((c["name"], "OK", f"{result} roles  site={c['site']}"))
        else:
            c["error"] = result
            rows.append((c["name"], "FAIL", result[:100]))
        print(f"{rows[-1][0]:<16} {rows[-1][1]:<5} {rows[-1][2]}", flush=True)

    json.dump(companies, open("companies.json", "w", encoding="utf-8"), indent=2)
    print("\nwrote companies.json:", sum(c.get("verified") for c in companies), "verified of", len(companies))


if __name__ == "__main__":
    main()
