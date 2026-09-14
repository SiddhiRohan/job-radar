"""skills_confirmed.md: the vocabulary tailoring may draw on, plus the JD-skill yes/no prompts."""

import sys
from pathlib import Path

PATH = Path("skills_confirmed.md")


def load():
    if not PATH.exists():
        return []
    return [line[2:].strip() for line in PATH.read_text(encoding="utf-8").splitlines() if line.startswith("- ")]


def text():
    """Lowercase blob of every confirmed term, used alongside the base resume text as the allowed vocabulary."""
    return "\n".join(load()).lower()


def add(term):
    if term.lower() not in {t.lower() for t in load()}:
        with PATH.open("a", encoding="utf-8") as f:
            f.write(f"- {term}\n")


def confirm(jd_skills, allow_prompt):
    """Ask 'JD asks for X. Have you used it? [y/n]' per skill. Returns (accepted, declined, deferred)."""
    accepted, declined, deferred = [], [], []
    interactive = allow_prompt and sys.stdin.isatty()
    for s in jd_skills:
        if not interactive:
            deferred.append(s)
            continue
        ans = input(f"JD asks for {s}. Have you used it? [y/n] ").strip().lower()
        if ans == "y":
            add(s)
            accepted.append(s)
        else:
            declined.append(s)
    return accepted, declined, deferred
