"""Merge verified candidates into companies.json with sponsors_h1b, sponsorship_source, and tier; write not_on_workday.json."""

import json
from collections import Counter

# Names that appeared in the top H-1B sponsor lists found on 2026-09-13 (careernomics top-100 FY2025, scoutify list).
# fmt: off
H1B_TOP = {"EY", "Amazon", "Deloitte", "Goldman Sachs", "Microsoft", "Walmart", "JPMorgan Chase", "Google", "Capital One",
           "Bank of America", "Infosys", "PwC", "Citi", "McKinsey", "Tesla", "EXL Service", "FedEx", "Morgan Stanley",
           "Tiger Analytics", "BlackRock", "Meta", "BCG", "Deutsche Bank", "KPMG", "Citadel", "Fidelity", "Cummins",
           "Home Depot", "Barclays", "Apple", "Siemens", "Grant Thornton", "American Express", "American Airlines", "Wipro",
           "Discover", "Eli Lilly", "Cognizant", "UBS", "Amgen", "ZS Associates", "Capgemini", "Cisco", "Accenture", "Micron",
           "IQVIA", "Uber", "BDO", "T-Mobile", "Adobe", "AbbVie", "Charter Communications", "ASML", "DoorDash", "Chewy",
           "Jefferies", "Wells Fargo", "Intel", "Medline", "Moody's", "Visa", "Intuit", "Optum", "PayPal", "LexisNexis",
           "Nomura", "Genpact", "ServiceNow", "HP", "Dell", "Wayfair", "Royal Bank of Canada", "Ford", "State Street",
           "Salesforce", "NVIDIA", "Qualcomm", "LinkedIn", "Stripe", "Airbnb", "Lyft", "Snowflake", "Databricks", "Palantir",
           "Coinbase", "Block", "Twilio", "Datadog", "MongoDB", "Oracle", "Netflix", "Crowe", "Thomson Reuters", "Workday",
           "Target", "Humana", "CVS Health", "KLA", "Mastercard", "Broadcom", "Marvell", "Analog Devices", "Applied Materials",
           "Merck", "Pfizer", "Bristol Myers Squibb", "Thermo Fisher", "Medtronic", "Abbott", "Elevance", "Cigna", "McKesson",
           "Cardinal Health", "Nasdaq", "S&P Global", "FactSet", "Vanguard", "US Bank", "PNC", "Truist", "Synchrony", "Ally",
           "Fannie Mae", "Freddie Mac", "TIAA", "Prudential", "Travelers", "Allstate", "Geico", "Autodesk", "CrowdStrike",
           "Zoom", "Expedia", "Booking", "Warner Bros Discovery", "Disney", "Comcast", "Verizon", "AT&T", "GM", "Toyota",
           "Nike", "Lowe's", "Caterpillar", "3M", "HPE", "Snap", "Proofpoint", "Guidehouse", "JLL", "T. Rowe Price", "SHI International"}
# fmt: on
# Defense and ITAR-heavy employers: postings routinely require clearance or citizenship.
# fmt: off
NO_SPONSOR = {"Booz Allen", "Leidos", "CACI", "GDIT", "Northrop Grumman", "Raytheon", "Boeing", "GE", "Lockheed Martin",
              "SAIC", "Peraton"}
# fmt: on
# Tier 1: core business is data, AI, fintech, or healthcare tech, and sponsors.
# fmt: off
TIER1 = {"Capital One", "NVIDIA", "Salesforce", "Adobe", "Intel", "Mastercard", "Visa", "PayPal", "Nasdaq", "S&P Global", "FactSet",
         "Workday", "Autodesk", "CrowdStrike", "Zoom", "Fidelity", "Vanguard", "BlackRock", "State Street", "Synchrony",
         "Ally", "Humana", "CVS Health", "Elevance", "Cigna", "IQVIA", "Proofpoint", "Snap", "Thomson Reuters", "LexisNexis",
         "T. Rowe Price", "Netflix", "Expedia", "Booking", "Chime", "Broadcom", "Micron", "KLA", "Marvell", "Cisco",
         "Morgan Stanley", "Citi", "Discover", "TIAA", "Intuit", "Truist", "Fannie Mae", "Freddie Mac", "Medline",
         "McKesson", "Cardinal Health", "Premier Inc", "WellSky", "Amplify", "Pax8"}
# fmt: on
# fmt: off
MAIN_SEED = {"NVIDIA", "Salesforce", "Adobe", "Intel", "Mastercard", "Visa", "Walmart", "Target", "KLA", "Fidelity",
             "Humana", "CVS Health"}  # seeded true by hand in round 2
# fmt: on


H1B_CHECK = {k: v for k, v in json.load(open("companies/h1b_check.json", encoding="utf-8")).items() if k[0] != "_"}


def sponsorship(name, existing):
    if name in NO_SPONSOR:
        return False, "defense contractor / postings say no sponsorship"
    if name in MAIN_SEED:
        return True, "seeded by hand (round 2)"
    if name in H1B_TOP:
        return True, "top H-1B sponsor lists (careernomics FY2025 top-100, scoutify)"
    if name in H1B_CHECK:
        return H1B_CHECK[name]["sponsors_h1b"], "FY2025 LCA lookup: " + H1B_CHECK[name]["fy2025"]
    if existing is not None:
        return existing, "kept from earlier companies.json"
    return None, "not found in H-1B lists"


def tier(name, sponsors):
    if name in TIER1 and sponsors:
        return 1
    return 2 if sponsors else 3


def main():
    companies = {c["name"]: c for c in json.load(open("companies.json", encoding="utf-8"))}
    cands = json.load(open("companies/candidates.json", encoding="utf-8"))
    for name, e in cands.items():
        if e.get("status") != "verified":
            continue
        c = companies.setdefault(name, {"name": name})
        c.update(
            tenant=e["tenant"],
            shard=e["shard"],
            site=e["site"],
            verified=True,
            verified_at=e.get("verified_at"),
            open_roles=e.get("open_roles"),
        )
    for name, c in companies.items():
        s, src = sponsorship(name, c.get("sponsors_h1b"))
        c["sponsors_h1b"], c["sponsorship_source"], c["tier"] = s, src, tier(name, s)
    out = sorted(companies.values(), key=lambda c: (c["tier"], c["name"]))
    json.dump(out, open("companies.json", "w", encoding="utf-8"), indent=2)
    not_wd = {
        n: {
            "ats": e.get("ats", "unknown"),
            "searches": e.get("misses", 0),
            "second_search": e.get("second_search"),
            "source": e.get("source"),
        }
        for n, e in cands.items()
        if e.get("status") in ("not_on_workday", "failed")
    }
    for n, e in cands.items():
        if e.get("status") == "failed":
            not_wd[n]["ats"] = f"Workday tenant found but failed verification twice: {e.get('error', '')[:80]}"
    json.dump(not_wd, open("companies/not_on_workday.json", "w", encoding="utf-8"), indent=1)
    print(
        "companies:",
        len(out),
        Counter(c["tier"] for c in out),
        "| sponsors:",
        Counter(str(c["sponsors_h1b"]) for c in out),
    )
    print("not_on_workday:", len(not_wd))


if __name__ == "__main__":
    main()
