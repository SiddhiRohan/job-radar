"""Build digests/YYYY-MM-DD.md from this run's new postings in jobs.jsonl."""
import json
import sys
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")


def load_jsonl(path):
    p = Path(path)
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()] if p.exists() else []


def score_of(j):
    v = j.get("verdict") or {}
    return v.get("score") if isinstance(v.get("score"), int) else 0  # 0 = unscored / error


def line(j):
    v = j.get("verdict") or {}
    s = score_of(j)
    score_txt = f"score {s}" if s else ("unscored" if "verdict" not in j else f"error: {v.get('error', '?')[:60]}")
    out = [f"- **{j['company']}** | {j['title']} | {j['location']} | {j['posted_on']} | {score_txt} | [link]({j['url']})"]
    if v.get("why"):
        out.append(f"    {v['why']}")
    if s in (3, 4) and v.get("hard_requirements_missing"):
        out.append(f"    missing: {', '.join(v['hard_requirements_missing'])}")
    if v.get("sponsorship_note"):
        out.append(f"    sponsorship: {v['sponsorship_note'][:200]}")
    return "\n".join(out)


def build(run, jobs):
    today = datetime.now().strftime("%Y-%m-%d")
    new = [j for j in jobs if j.get("first_seen") == run.get("ran_at")]
    md = [f"# Job radar digest {today}", "",
          f"Companies polled: {run.get('companies_polled', 0)} | Window: last {run.get('max_days_ago', '?')} day(s) | "
          f"New postings: {len(new)}", ""]
    for s in (5, 4, 3, 2, 1, 0):
        group = sorted((j for j in new if score_of(j) == s), key=lambda j: (j["company"], j["title"]))
        if not group:
            continue
        md += [f"## {'Score ' + str(s) if s else 'Unscored'} ({len(group)})", ""]
        md += [line(j) for j in group]
        md.append("")
    errors = run.get("errors") or {}
    md += ["## Companies that errored", ""]
    md += [f"- {name}: {err[:120]}" for name, err in errors.items()] or ["- none"]
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
