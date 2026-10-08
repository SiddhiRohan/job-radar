"""One checked change to a list setting in config.json: add an entry or remove one. The filter auditor suggests such
changes and the person applies them; nothing here runs unless they do."""

import json
import re
from pathlib import Path

PATH = Path("config.json")


def load():
    try:
        return json.loads(PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def problem(change, settings):
    """Why {setting, action, value} cannot be made against these settings, or ""."""
    now = settings.get(change["setting"], [])
    if change["action"] == "remove" and change["value"] not in now:
        return f"{change['setting']} has no entry {change['value']!r} to remove"
    if change["action"] == "add" and change["value"] in now:
        return f"{change['setting']} already has {change['value']!r}"
    if change["setting"].endswith("patterns"):
        try:
            re.compile(change["value"])
        except re.error:
            return f"{change['value']!r} is not a valid pattern"
    return ""


def make(change):
    """Make the change in config.json, keeping its layout. Returns "" when made, else why not."""
    cfg = load()
    if why := problem(change, cfg):
        return why
    values = list(cfg.get(change["setting"], []))
    values.append(change["value"]) if change["action"] == "add" else values.remove(change["value"])
    PATH.write_text(json.dumps(cfg | {change["setting"]: values}, indent=2) + "\n", encoding="utf-8")
    return ""
