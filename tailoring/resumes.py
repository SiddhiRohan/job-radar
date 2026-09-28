"""Locate resume bases and role variants under Resume/, and extract .docx text with the stdlib.

Two layouts work. The simple one: a resume file directly in Resume/ (resume.docx), or two files whose names start
with "entry" and "experienced". The original one: Entry/1 Page and Experienced/V1/<role>/<length> folders holding
the same file name, which also gives the scorer role folders to recommend. The original wins when present."""

import html
import re
import zipfile
from pathlib import Path

from radar import owner

ROOT = Path("Resume")
BASE_NAME = owner.resume_filename()  # e.g. "Resume - Jane Public.docx", set in .env
ENTRY_BASE = ROOT / "Entry" / "1 Page" / BASE_NAME
EXPERIENCED_DIR = ROOT / "Experienced" / "V1"
EXPERIENCED_BASE = EXPERIENCED_DIR / "DS and DE Resumes" / "2 Page" / BASE_NAME
VARIANT_DIRS = {"one-page": "1 Page", "two-page": "2 Page"}
TEXT_KINDS = (".docx", ".txt", ".md")
NO_PROFILE = "(no profile.md yet: judge the candidate from the resume alone)"


def docx_text(path):
    """Paragraph text from a .docx: it is a zip, paragraphs are <w:p>, runs are <w:t>."""
    xml = zipfile.ZipFile(path).read("word/document.xml").decode("utf-8")
    xml = re.sub(r"<w:tab/>", " ", xml)
    paras = re.findall(r"<w:p[ >].*?</w:p>", xml, flags=re.S)
    return "\n".join(html.unescape("".join(re.findall(r"<w:t(?:\s[^>]*)?>(.*?)</w:t>", p, flags=re.S))) for p in paras)


def legacy():
    return ENTRY_BASE.exists() and EXPERIENCED_BASE.exists()


def loose_files():
    """Resume files placed directly in Resume/, skipping Word's lock files."""
    if not ROOT.is_dir():
        return []
    return sorted(p for p in ROOT.iterdir() if p.is_file() and p.suffix.lower() in TEXT_KINDS and p.name[:2] != "~$")


def base_paths():
    """{"entry": path, "experienced": path}, or {} when no resume is found. One resume serves as both bases."""
    if legacy():
        return {"entry": ENTRY_BASE, "experienced": EXPERIENCED_BASE}
    files = loose_files()
    named = {k: next((p for p in files if p.stem.lower().startswith(k)), None) for k in ("entry", "experienced")}
    if named["entry"] and named["experienced"]:
        return named
    one = (
        named["experienced"] or named["entry"] or next((p for p in files if p.stem.lower().startswith("resume")), None)
    )
    one = one or (files[0] if len(files) == 1 else None)
    return {"entry": one, "experienced": one} if one else {}


def text_of(path):
    return docx_text(path) if path.suffix.lower() == ".docx" else path.read_text(encoding="utf-8", errors="ignore")


def bases():
    paths = base_paths()
    if not paths:
        raise FileNotFoundError(
            "no resume found: put yours in Resume/ as resume.docx (or entry.docx and experienced.docx)"
        )
    return {k: text_of(p) for k, p in paths.items()}


def profile_text():
    p = Path("profile.md")
    return p.read_text(encoding="utf-8") if p.exists() else NO_PROFILE


def role_folders():
    return sorted(p.name for p in EXPERIENCED_DIR.iterdir() if p.is_dir()) if EXPERIENCED_DIR.is_dir() else []


def variant_path(role, variant):
    return EXPERIENCED_DIR / role / VARIANT_DIRS[variant] / BASE_NAME


def role_status():
    """{role: {variant: exists}} so the scorer can name real folders and apply.py knows what to build."""
    return {r: {v: variant_path(r, v).exists() for v in VARIANT_DIRS} for r in role_folders()}


def tailored_folders():
    if not ROOT.is_dir():
        return []
    return sorted(p.name for p in ROOT.iterdir() if p.is_dir() and p.name.startswith("For "))
