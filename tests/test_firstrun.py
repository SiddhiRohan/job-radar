"""The setup page's saves: resume, API key and profile. The key is checked, stored in .env, and never sent back."""

import base64

import pytest
import requests

from radar import firstrun

KEY = "sk-ant-api03-" + "x" * 40


class Reply:
    def __init__(self, code):
        self.status_code = code


def b64(data):
    return base64.b64encode(data).decode()


def test_resume_is_saved_and_replaced(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert firstrun.save_resume("My CV.docx", b64(b"PK first")) == "resume.docx"
    assert firstrun.save_resume("cv.txt", b64(b"second")) == "resume.txt"
    assert sorted(p.name for p in (tmp_path / "Resume").iterdir()) == ["resume.txt"]  # one resume at a time


def test_wrong_files_are_refused(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(ValueError, match="Word file"):
        firstrun.save_resume("cv.pdf", b64(b"%PDF"))
    with pytest.raises(ValueError, match="5 MB"):
        firstrun.save_resume("cv.docx", b64(b"x" * (firstrun.MAX_BYTES + 1)))
    with pytest.raises(ValueError):
        firstrun.save_resume("cv.docx", "not base64!!")


def test_env_keeps_other_lines(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("# comment\nGMAIL_ADDRESS=me@example.com\nANTHROPIC_API_KEY=old\n", encoding="utf-8")
    firstrun.write_env("ANTHROPIC_API_KEY", "new")
    firstrun.write_env("OWNER_SHORT", "Jane")
    text = (tmp_path / ".env").read_text(encoding="utf-8")
    assert text == "# comment\nGMAIL_ADDRESS=me@example.com\nANTHROPIC_API_KEY=new\nOWNER_SHORT=Jane\n"


def test_key_is_checked_saved_and_never_sent_back(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert firstrun.save_key(KEY, post=lambda *a, **k: Reply(200)) == "ok"
    assert firstrun.read_env()["ANTHROPIC_API_KEY"] == KEY
    state = firstrun.state()
    assert state["key_set"] is True and KEY not in str(state)


def test_bad_or_rejected_keys_are_not_saved(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(ValueError, match="sk-ant-"):
        firstrun.save_key("hello")
    with pytest.raises(ValueError, match="did not accept"):
        firstrun.save_key(KEY, post=lambda *a, **k: Reply(401))
    assert not (tmp_path / ".env").exists()


def test_offline_key_is_saved_unchecked(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    def offline(*a, **k):
        raise requests.ConnectionError("no network")

    assert firstrun.save_key(KEY, post=offline) == "unchecked"


def test_profile_is_required_to_have_words(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(ValueError):
        firstrun.save_profile("   ")
    firstrun.save_profile("Roles I want: data engineer")
    assert firstrun.state()["profile"].startswith("Roles I want")
