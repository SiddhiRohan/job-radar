"""Every radar command the assistant guide and the slash commands name is a module that exists."""

import re
from pathlib import Path

FILES = [Path("CLAUDE.md"), *sorted(Path(".claude/commands").glob("*.md"))]


def test_every_module_a_guide_names_exists():
    named = {
        m
        for f in FILES
        for m in re.findall(r"python -m ((?:radar|tailoring|companies)\.\w+)", f.read_text(encoding="utf-8"))
    }
    missing = [m for m in sorted(named) if not Path(*m.split(".")).with_suffix(".py").exists()]
    assert "radar.agents" in named and "radar.sponsormap" in named
    assert missing == []


def test_every_agent_subcommand_a_guide_names_is_one_the_cli_knows():
    used = {c for f in FILES for c in re.findall(r"python -m radar\.agents (\w+)", f.read_text(encoding="utf-8"))}
    assert used <= {"run", "next", "save", "show", "debrief", "audit"}
