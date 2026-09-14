"""Build skills_confirmed.md from every .docx under Resume/: Skills lines, bold segments, and mixed-case/acronym tokens."""

import re
from pathlib import Path

from docx import Document

import tailor

# fmt: off
STOP = {"University", "Maryland", "College", "Park", "Washington", "India", "Bengaluru", "Hyderabad", "United", "States",
        "America", "Relocation", "Open", "Data", "Engineer", "Scientist", "Present", "Aug", "Dec", "May", "June", "July",
        "Jan", "Feb", "Mar", "Apr", "Sep", "Oct", "Nov", "Master", "Science", "GPA", "Coursework", "Portfolio", "GitHub",
        "Siddhi", "Rohan", "Chakka", "Adventaus", "Technologies", "Pvt", "Ltd", "StackNexus", "ENST", "AREC", "UMD", "USDA",
        "Hebrew", "Pedon", "English", "Have", "Built", "Owned", "Designed", "Developed", "Delivered", "Led", "Scoped",
        "Modeled", "Mined", "Drove", "Scaled", "Shipped", "Launched", "Partnered", "Structured", "Served", "Set", "Defined",
        "Reframed", "Established", "Productionized", "Instrumented", "Overhauled", "Automated", "Translated", "Quantified",
        "Standardized", "Engineered", "Architected", "Institutionalized", "Research", "Publications", "Neural", "Network",
        "International", "Conference", "Cognitive", "Machine", "Learning", "Analog", "Synthesizer", "Character", "Digital",
        "Sound", "Processing", "Synthesis", "Projects", "Morpheus", "Arbiter", "MedPal", "Professional", "Summary", "Work",
        "Experience", "Skills", "Education", "The", "This", "Own", "Deliver", "Repeatedly", "Comfortable", "Applied"}
# fmt: on


def terms_from_doc(path):
    doc = Document(path)
    found = set()
    section = None
    for p in doc.paragraphs:
        t = p.text.strip()
        if not t:
            continue
        if t.rstrip("\t").upper() in tailor.HEADINGS:
            section = t.rstrip("\t").upper()
            continue
        if section == "SKILLS":
            found |= {s.strip(" .\t") for s in re.split(r",|;|\band\b(?= [A-Z])", t) if 2 < len(s.strip()) < 60}
        for m in re.finditer(r"\*\*(.+?)\*\*", tailor.marked_text(p)):
            seg = m.group(1).strip(" ,.;:")
            if 2 < len(seg) < 70 and not re.search(r"\d", seg):
                found.add(seg)
        for tok in re.findall(r"[A-Za-z][A-Za-z0-9+#./\-]*[A-Za-z0-9+#]", t):
            if (
                (
                    re.search(r"[A-Z]", tok[1:])
                    or tok.isupper()
                    or "/" in tok
                    or "-" in tok
                    or tok in ("dbt", "scikit-learn")
                )
                and tok not in STOP
                and not tok.isdigit()
                and len(tok) > 1
            ):
                found.add(tok)
    return found


def main():
    allterms, sources = set(), {}
    for path in sorted(Path("Resume").rglob("*.docx")):
        for t in terms_from_doc(path):
            allterms.add(t)
            sources.setdefault(t, path.parts[1] + ("/" + path.parts[2] if len(path.parts) > 3 else ""))
    lines = [
        "# Confirmed skills",
        "",
        "Every tool, library, platform, method, and domain term found under Resume/ on "
        "2026-09-13, one per line. Add anything you have actually used. Tailoring may use any line here.",
        "",
    ]
    lines += sorted(f"- {t}" for t in allterms)
    Path("skills_confirmed.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
