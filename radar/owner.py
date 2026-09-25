"""Who this radar runs for. Personal details live in .env (ignored by git), never in code or docs.

.env keys, all optional:
  OWNER_NAME        full name used to sign letters and as the document author, e.g. "Jane Q. Public"
  OWNER_SHORT       first name the assistant uses, e.g. "Jane"
  RESUME_FILENAME   file name of the base resumes under Resume/, e.g. "Resume - Jane Public.docx"
  SKILLS_STOPWORDS  comma-separated proper nouns (your name, employers, schools) that are not skills
"""

import os
from pathlib import Path


def env(name, default=""):
    if os.environ.get(name):
        return os.environ[name]
    if Path(".env").exists():
        for raw in Path(".env").read_text(encoding="utf-8").splitlines():
            key, _, value = raw.strip().partition("=")
            if key == name and value.strip():
                return value.strip().strip('"').strip("'")
    return default


def name():
    return env("OWNER_NAME", "the owner")


def short_name():
    return env("OWNER_SHORT", name().split()[0] if name() != "the owner" else "the owner")


def resume_filename():
    return env("RESUME_FILENAME", "Resume.docx")


def resume_stem():
    return resume_filename().rsplit(".", 1)[0]


def skills_stopwords():
    return {w.strip() for w in env("SKILLS_STOPWORDS", "").split(",") if w.strip()}
