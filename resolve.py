"""Verify resolved candidates in candidates.json against Workday (empty search, read total). Two attempts, 1.5 s gap."""

import json
import sys
import time
from datetime import datetime, timezone

import wd

sys.stdout.reconfigure(encoding="utf-8")
P = "candidates.json"


def main():
    c = json.load(open(P, encoding="utf-8"))
    todo = [(n, e) for n, e in c.items() if e.get("status") == "resolved"]
    print(f"verifying {len(todo)} resolved tenants")
    for name, e in todo:
        err = None
        for attempt in range(2):
            try:
                e["open_roles"] = wd.count(e["tenant"], e["shard"], e["site"])
                e["status"], e["verified_at"], err = (
                    "verified",
                    datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    None,
                )
                break
            except Exception as ex:
                err = str(ex)[:120]
                time.sleep(1.5)
        if err:
            e["status"], e["error"] = "failed", err
        print(f"  {name:<24} {e['status']:<9} {e.get('open_roles', '')} {err or ''}", flush=True)
        latest = json.load(open(P, encoding="utf-8"))  # merge: other tools edit this file while we run
        latest.setdefault(name, {}).update(e)
        json.dump(latest, open(P, "w", encoding="utf-8"), indent=1)
        c = latest
    from collections import Counter

    print(Counter(e.get("status") for e in c.values()))


if __name__ == "__main__":
    main()
