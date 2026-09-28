"""A new user's letters are signed with the name on their resume, never "the owner", and the letter routes work
without profile.md, which is optional. Offline: the model call is replaced."""

from docx import Document

from radar import owner
from tailoring import letters


def test_without_a_name_the_letter_takes_it_from_the_resume(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("OWNER_NAME", raising=False)
    monkeypatch.delenv("OWNER_SHORT", raising=False)
    assert "top of the resume" in owner.signature() and "first name" in owner.signature(short=True)
    seen = []
    monkeypatch.setattr(letters.llm, "complete", lambda system, user, *a, **k: (seen.append(system) or "Dear team", 0))
    letters.cover_letter({"title": "Data Engineer", "company": "Contoso", "location": "Austin"}, "JD", "", "Resume")
    assert "sign-off with the candidate's full name as it appears at the top of the resume" in seen[0]
    assert "the owner" not in seen[0]


def test_a_name_in_env_is_used_as_given(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("OWNER_NAME", "Jane Q. Public")
    monkeypatch.delenv("OWNER_SHORT", raising=False)
    assert owner.signature() == "Jane Q. Public" and owner.signature(short=True) == "Jane"


def test_a_letter_without_a_name_has_no_author(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("OWNER_NAME", raising=False)
    base = tmp_path / "base.docx"
    Document().save(base)
    letters.write_docx("Dear team,\nThank you.", tmp_path / "letter.docx", base)
    assert Document(tmp_path / "letter.docx").core_properties.author == ""
