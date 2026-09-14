"""finalize.py <folder>: humanize prose, strip invisible Unicode and provenance metadata from every outgoing file."""

import difflib
import os
import re
import sys
from pathlib import Path

import requests
from docx import Document

from radar import llm
from tailoring import tailor

sys.stdout.reconfigure(encoding="utf-8")
SERVICE = os.environ.get("WATERMARKS_SERVICE_URL", "http://127.0.0.1:8765")
INVISIBLE = re.compile("[​-‏‪-‮⁠-⁤﻿­︀-️᠎  ]")
ODD_SPACE = re.compile("[  -   　]")
HUMANIZE = """Rewrite each paragraph so it reads like a careful person wrote it: vary sentence rhythm and length, replace
formulaic transitions and filler with concrete phrasing, plain varied wording. Keep every fact, number, name, tool,
and identifier exactly as given. Add nothing, remove nothing. Keep **bold** markers where they are. No em dashes.
Return a JSON array of strings, same length and order as the input."""
SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {"paragraphs": {"type": "array", "items": {"type": "string"}}},
    "required": ["paragraphs"],
}


def clean(s):
    return ODD_SPACE.sub(" ", INVISIBLE.sub("", s))


def facts_kept(old, new):
    return (
        re.findall(r"\d[\d,.%+]*", old) == re.findall(r"\d[\d,.%+]*", new) and 0.6 <= len(new) / max(len(old), 1) <= 1.5
    )


def humanize(paragraphs):
    """Return rewritten list; any paragraph that changes a number or length too much keeps its original."""
    if not paragraphs:
        return []
    out, _ = llm.complete(
        HUMANIZE, "\n".join(f"[{i}] {p}" for i, p in enumerate(paragraphs)) + "\n\nReturn JSON.", SCHEMA
    )
    new = out["paragraphs"]
    return [
        n if len(new) == len(paragraphs) and facts_kept(o, n) else o
        for o, n in zip(paragraphs, new + paragraphs[len(new) :])
    ]


def strip_docx_props(doc):
    cp, removed = doc.core_properties, []
    for f in ("author", "last_modified_by", "title", "subject", "keywords", "comments", "category", "content_status"):
        if getattr(cp, f):
            removed.append(f)
            setattr(cp, f, "")
    cp.revision = 1
    for part in doc.part.package.parts:
        if str(part.partname) == "/docProps/app.xml":
            part._blob = (
                b'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Properties xmlns="http://schemas.'
                b'openxmlformats.org/officeDocument/2006/extended-properties"><Application></Application>'
                b"<Company></Company></Properties>"
            )
            removed.append("app.xml(Application, Company)")
    return removed


def service_clean(path):
    """Use the remove-ai-marks service when it is up; return a report line or None."""
    try:
        if not requests.get(f"{SERVICE}/health", timeout=3).ok:
            return None
        with open(path, "rb") as f:
            insp = requests.post(f"{SERVICE}/inspect", files={"file": f}, timeout=60).json()
        with open(path, "rb") as f:
            r = requests.post(f"{SERVICE}/clean", files={"file": f}, timeout=120)
        r.raise_for_status()
        Path(path).write_bytes(r.content)
        return f"service: {insp}"
    except requests.RequestException:
        return None


def finalize_docx(path, report):
    doc = Document(path)

    def is_prose(p):  # skip headers (tabs, dates, pipes) and anything carrying a hyperlink, which a rewrite would drop
        return (
            p.text.strip()
            and "|" not in p.text
            and "\t" not in p.text
            and len(p.text.split()) > 6
            and not tailor.DATE.search(p.text)
            and not p._p.xpath(".//w:hyperlink")
        )

    prose = [p for p in doc.paragraphs if is_prose(p)]
    before = [tailor.marked_text(p) for p in prose]
    after = humanize(before)
    changed = 0
    for p, b, a in zip(prose, before, after):
        if a != b:
            changed += 1
            tailor.set_text(p, a)
            report.append("\n".join(difflib.unified_diff([b], [a], lineterm="", n=0))[:2000])
    stripped = 0
    for p in doc.paragraphs:
        for r in p.runs:
            c = clean(r.text)
            if c != r.text:
                stripped += 1
                r.text = c
    props = strip_docx_props(doc)
    doc.save(path)
    report.append(
        f"{path.name}: humanized {changed}/{len(prose)} paragraphs; runs with invisible chars stripped: {stripped}; "
        f"properties cleared: {', '.join(props) or 'none already set'}; "
        + (service_clean(path) or "service: not running")
    )


def finalize_text(path, report, humanize_prose):
    text = path.read_text(encoding="utf-8")
    c = clean(text)
    if humanize_prose:
        paras = [p for p in c.split("\n\n") if p.strip() and not p.startswith("#")]
        new = humanize(paras)
        for b, a in zip(paras, new):
            if a != b:
                c = c.replace(b, a)
                report.append("\n".join(difflib.unified_diff([b], [a], lineterm="", n=0))[:2000])
    path.write_text(c, encoding="utf-8")
    report.append(
        f"{path.name}: invisible chars removed: {len(INVISIBLE.findall(text)) + len(ODD_SPACE.findall(text))}"
    )


def main():
    folder = Path(sys.argv[1])
    report = [f"# finalize report for {folder}", ""]
    for p in sorted(folder.glob("*.docx")):
        finalize_docx(p, report)
    for p in sorted(folder.glob("outreach.md")):
        finalize_text(p, report, humanize_prose=True)
    for p in list(folder.glob("*.md")) + list(folder.glob("*.txt")) + list(Path("digests").glob("*.md")):
        if p.name != "outreach.md":
            finalize_text(p, report, humanize_prose=False)
    if not _service_reachable():
        report.append(
            f"remove-ai-marks service not running at {SERVICE}; used local fallback. Start it and set "
            "WATERMARKS_SERVICE_URL to use /inspect and /clean. No PDFs were produced, so exiftool/qpdf were not needed."
        )
    text = "\n".join(report) + "\n"
    print(text)
    with open(folder / "notes.md", "a", encoding="utf-8") as f:
        f.write("\n\n" + text)


def _service_reachable():
    try:
        return requests.get(f"{SERVICE}/health", timeout=3).ok
    except requests.RequestException:
        return False


if __name__ == "__main__":
    main()
