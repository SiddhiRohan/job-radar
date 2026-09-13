"""Cover letters and outreach text via Claude, plus a .docx writer that mirrors the base resume's page setup."""
from docx import Document
from docx.shared import Pt

import llm

COVER_RULES = """Write a one-page cover letter for this posting. Role and company specific. Add to the resume rather than
repeating it: pick two or three things from the resume that matter for THIS job and say why, in plain human voice.
No buzzwords, no visa or sponsorship mention, no em dashes, no bullet points. About 250-320 words.
Format: greeting line, 3-4 short paragraphs, sign-off with the name Rohan Chakka. Return only the letter text."""

OUTREACH_SCHEMA = {"type": "object", "additionalProperties": False,
                   "properties": {"linkedin_note": {"type": "string"}, "message": {"type": "string"}},
                   "required": ["linkedin_note", "message"]}
OUTREACH_RULES = """Write cold outreach for this posting. Two pieces:
1. linkedin_note: a LinkedIn connection note UNDER 300 characters (aim 250-270). No name sign-off. Mention the role.
2. message: a DM or application message of 100-120 words, plain and specific to the company and role, no buzzwords.
No visa or sponsorship mention anywhere. No em dashes. Sign the message as Rohan only if it reads naturally."""


def cover_letter(job, jd, profile, resume_text):
    user = (f"POSTING: {job['title']} at {job['company']} ({job.get('detail_location') or job['location']})\n"
            f"{jd[:10000]}\n\nTAILORED RESUME:\n{resume_text[:8000]}\n\nWrite the letter.")
    text, _ = llm.complete(COVER_RULES + "\n\nCANDIDATE PROFILE:\n" + profile, user, max_tokens=2000)
    return text.replace("—", "-").strip()


def outreach(job, jd, profile):
    user = f"POSTING: {job['title']} at {job['company']}\n{jd[:8000]}\n\nWrite both pieces."
    for _ in range(2):
        o, _ = llm.complete(OUTREACH_RULES + "\n\nCANDIDATE PROFILE:\n" + profile, user, OUTREACH_SCHEMA)
        o = {k: v.replace("—", "-").strip() for k, v in o.items()}
        if len(o["linkedin_note"]) < 300 and 90 <= len(o["message"].split()) <= 130:
            return o
        user += f"\n\nPrevious attempt was out of range (note {len(o['linkedin_note'])} chars, message " \
                f"{len(o['message'].split())} words). Fix the lengths."
    return o


def write_docx(text, out_path, base_path):
    """One-page letter with the base resume's margins and an 11pt body in the base's inherited font."""
    base = Document(base_path).sections[0]
    doc = Document()
    s = doc.sections[0]
    s.page_width, s.page_height = base.page_width, base.page_height
    s.top_margin, s.bottom_margin = max(base.top_margin, Pt(54)), max(base.bottom_margin, Pt(54))
    s.left_margin, s.right_margin = max(base.left_margin, Pt(54)), max(base.right_margin, Pt(54))
    doc.styles["Normal"].font.size = Pt(11)
    for para in [p for p in text.split("\n") if p.strip()]:
        doc.add_paragraph(para.strip())
    doc.core_properties.author = "Siddhi Rohan Chakka"
    doc.save(out_path)
