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


def test_letter_routes_run_without_a_profile(tmp_path, monkeypatch):
    import importlib
    import io
    import sys

    with monkeypatch.context() as patch:
        patch.setattr(sys, "stdout", io.TextIOWrapper(io.BytesIO(), encoding="utf-8"))
        server = importlib.import_module("server")
    monkeypatch.chdir(tmp_path)  # no profile.md here
    monkeypatch.setattr(server.applier, "find_job", lambda company, req_id: {"company": company, "req_id": req_id})
    got = []
    monkeypatch.setattr(server.letters, "outreach", lambda j, jd, profile, text: got.append(profile) or {"ok": 1})

    class Inline:
        def __init__(self, target, daemon):
            self.target = target

        def start(self):
            self.target()

    monkeypatch.setattr(server.threading, "Thread", Inline)
    job = server.start_outreach({"company": "Contoso", "req_id": "R1", "sections": []})["job_id"]
    assert server.job_status(job)["status"] == "done" and got == [server.resumes.NO_PROFILE]
