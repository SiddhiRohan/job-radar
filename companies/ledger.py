"""Tiny helper for candidates.json: python -m companies.ledger set NAME tenant shard site | miss NAME [ats] | show"""

import json
import sys
from collections import Counter

P = "companies/candidates.json"


def main():
    c = json.load(open(P, encoding="utf-8"))
    cmd = sys.argv[1] if len(sys.argv) > 1 else "show"
    if cmd == "set":
        name, tenant, shard, site = sys.argv[2:6]
        c[name] = {"tenant": tenant, "shard": shard, "site": site, "status": "resolved", "source": "web search"}
    elif cmd == "miss":
        name = sys.argv[2]
        e = c.setdefault(name, {})
        e["misses"] = e.get("misses", 0) + 1
        e["ats"] = " ".join(sys.argv[3:]) or e.get("ats", "unknown")
        e["status"] = "not_on_workday" if e["misses"] >= 2 else "todo"
    elif cmd == "show":
        print(Counter(e.get("status") for e in c.values()))
        print("todo:", [n for n, e in c.items() if e.get("status") == "todo"])
    json.dump(c, open(P, "w", encoding="utf-8"), indent=1)


if __name__ == "__main__":
    main()
