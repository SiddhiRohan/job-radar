"""Locate resume bases and role variants under Resume/, and extract .docx text with the stdlib."""
import html
import re
import zipfile
from pathlib import Path

ROOT = Path("Resume")
ENTRY_BASE = ROOT / "Entry" / "1 Page" / "Resume - Siddhi Rohan.docx"
EXPERIENCED_DIR = ROOT / "Experienced" / "V1"
EXPERIENCED_BASE = EXPERIENCED_DIR / "DS and DE Resumes" / "2 Page" / "Resume - Siddhi Rohan.docx"
VARIANT_DIRS = {"one-page": "1 Page", "two-page": "2 Page"}
BASE_NAME = "Resume - Siddhi Rohan.docx"


def docx_text(path):
    """Paragraph text from a .docx: it is a zip, paragraphs are <w:p>, runs are <w:t>."""
    xml = zipfile.ZipFile(path).read("word/document.xml").decode("utf-8")
    xml = re.sub(r"<w:tab/>", " ", xml)
    paras = re.findall(r"<w:p[ >].*?</w:p>", xml, flags=re.S)
    return "\n".join(html.unescape("".join(re.findall(r"<w:t(?:\s[^>]*)?>(.*?)</w:t>", p, flags=re.S)))
                     for p in paras)


def bases():
    return {"entry": docx_text(ENTRY_BASE), "experienced": docx_text(EXPERIENCED_BASE)}


def role_folders():
    return sorted(p.name for p in EXPERIENCED_DIR.iterdir() if p.is_dir())


def variant_path(role, variant):
    return EXPERIENCED_DIR / role / VARIANT_DIRS[variant] / BASE_NAME


def role_status():
    """{role: {variant: exists}} so the scorer can name real folders and apply.py knows what to build."""
    return {r: {v: variant_path(r, v).exists() for v in VARIANT_DIRS} for r in role_folders()}


def tailored_folders():
    return sorted(p.name for p in ROOT.iterdir() if p.is_dir() and p.name.startswith("For "))
