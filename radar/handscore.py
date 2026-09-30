"""python -m radar.handscore next [N] | save <file>: score new postings with a coding assistant, no API key needed.

next writes the next N postings waiting for a score (10 by default), in the order a run scores them, to
.cache/to_score.json, together with the rules and verdict schema from radar/fit.py and the person's resumes and
profile. The assistant judges each posting and writes {"<id>": verdict} to a file. save checks every verdict against
the schema, stores the valid ones in jobs.jsonl marked scored_with "assistant", and says what is wrong with the rest
so they can be fixed and saved again. A posting a hard rule decides (years gate, sponsorship no) is left to the run,
which settles it without a model."""

import json
import sys
from pathlib import Path

from radar import fit, score, store
from tailoring import resumes

OUT = Path(".cache/to_score.json")
TYPES = {"string": str, "integer": int, "boolean": bool, "array": list, "object": dict, "null": type(None)}
HOW = (
    "Judge each posting as the rules say, against both resumes, from the posting text alone. Answer with one JSON "
    'object {"<id>": verdict, ...}; every verdict follows the schema exactly, factors first.'
)


def problems(value, schema, where="verdict"):
    """What breaks the schema, for the part of JSON Schema that radar/fit.py uses."""
    kinds = schema.get("type", [])
    kinds = [kinds] if isinstance(kinds, str) else kinds
    fits = [k for k in kinds if isinstance(value, TYPES[k]) and not (k == "integer" and isinstance(value, bool))]
    if kinds and not fits:
        return [f"{where} should be {' or '.join(kinds)}"]
    if "enum" in schema and value not in schema["enum"]:
        return [f"{where} should be one of {', '.join(map(str, schema['enum']))}"]
    found = []
    if isinstance(value, dict) and "properties" in schema:
        found += [f"{where}.{k} is missing" for k in schema.get("required", []) if k not in value]
        found += [f"{where}.{k} is not a verdict field" for k in value if k not in schema["properties"]]
        for k, sub in schema["properties"].items():
            found += problems(value[k], sub, f"{where}.{k}") if k in value else []
    if isinstance(value, list) and "items" in schema:
        for i, item in enumerate(value):
            found += problems(item, schema["items"], f"{where}.{i}")
    return found


def check(verdict):
    """Problems with one verdict: the schema, then the four factors in their order, which the schema cannot say."""
    found = problems(verdict, fit.SCHEMA)
    if not found and [f["factor"] for f in verdict["factors"]] != list(fit.MODEL_FACTORS):
        found.append("verdict.factors should be " + ", ".join(fit.MODEL_FACTORS) + ", once each, in that order")
    return found


def posting(j):
    return {
        "id": store.key(j),
        "title": j["title"],
        "company": j["company"],
        "location": j.get("location", ""),
        "sponsorship_read": j.get("sponsorship"),
        "sponsorship_phrase": j.get("sponsorship_evidence"),
        "description": j.get("description", "")[: score.MAX_DESC_CHARS],
    }


def next_batch(n=10, jobs=None):
    """Write the next n postings that need judging, with all it takes to judge them; return their ids."""
    todo = [j for j in score.queue(store.load() if jobs is None else jobs) if score.rule_verdict(j) is None][:n]
    bases = resumes.bases()
    packet = {"how": HOW, "rules": fit.RULES, "schema": fit.SCHEMA, "profile": resumes.profile_text()}
    packet |= {"entry_resume": bases["entry"], "experienced_resume": bases["experienced"]}
    packet["postings"] = [posting(j) for j in todo]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(packet, indent=1), encoding="utf-8")
    return [store.key(j) for j in todo]


def save(verdicts, jobs=None):
    """Store each valid verdict on its posting. Returns (stored ids, {id: problems})."""
    if not isinstance(verdicts, dict):
        raise ValueError('the file should hold one JSON object, {"<id>": verdict, ...}')
    jobs = store.load() if jobs is None else jobs
    by_id, stored, rejected = {store.key(j): j for j in jobs}, [], {}
    for pid, verdict in verdicts.items():
        found = check(verdict) if pid in by_id else ["no stored posting has this id"]
        if found:
            rejected[pid] = found
            continue
        by_id[pid] |= {"verdict": verdict, "scored_with": "assistant"}
        stored.append(pid)
    if stored:
        store.save(jobs)
    return stored, rejected


def main(argv):
    try:
        if argv[:1] == ["next"]:
            ids = next_batch(int(argv[1]) if len(argv) > 1 else 10)
            print(f"to judge: {len(ids)}, in {OUT}" if ids else "no posting is waiting for a score")
            return 0
        if argv[:1] == ["save"] and len(argv) == 2:
            stored, rejected = save(json.loads(Path(argv[1]).read_text(encoding="utf-8")))
            print(f"stored: {len(stored)}" + (", now run python -m radar.digest" if stored else ""))
            for pid, found in rejected.items():
                print(f"  not stored, {pid}: " + "; ".join(found[:4]))
            return 1 if rejected else 0
    except (OSError, ValueError) as e:
        print(f"could not {argv[0]}: {e}")
        return 1
    print(__doc__.splitlines()[0])
    return 2


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main(sys.argv[1:]))
