"""The doctor: a fresh folder lists what to fix; a set-up folder is ready; the brief mode prints only problems."""

import json

from docx import Document

from radar import doctor


def fresh(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "config.json").write_text("{}", encoding="utf-8")
    (tmp_path / "companies.json").write_text(json.dumps([{"name": "Contoso", "verified": True}]), encoding="utf-8")


def levels(found):
    return {c["what"].split(":")[0]: c["level"] for c in found}


def test_a_fresh_folder_says_what_to_fix(tmp_path, monkeypatch):
    fresh(tmp_path, monkeypatch)
    got = levels(doctor.checks())
    assert got["No resume found"] == "fix" and got["No Anthropic API key"] == "fix"
    assert got["No profile.md"] == "info" and got["Email statuses off"] == "info" and got["No run yet"] == "info"
    assert got["1 employers to poll"] == "ok"
    assert doctor.main([]) == 1


def test_a_set_up_folder_is_ready(tmp_path, monkeypatch, capsys):
    fresh(tmp_path, monkeypatch)
    (tmp_path / "Resume").mkdir()
    doc = Document()
    doc.add_paragraph("Data engineer")
    doc.save(tmp_path / "Resume" / "resume.docx")
    (tmp_path / ".env").write_text("ANTHROPIC_API_KEY=sk-test\n", encoding="utf-8")
    (tmp_path / "last_run.json").write_text(json.dumps({"ran_at": "2020-01-01T07:30:00+00:00"}), encoding="utf-8")
    assert doctor.main(["--brief"]) == 0
    out = capsys.readouterr().out
    assert "doctor: ready" in out and "Resume" not in out  # brief mode hides what is fine
    assert "over a day ago" in out


def test_a_broken_config_is_a_fix(tmp_path, monkeypatch):
    fresh(tmp_path, monkeypatch)
    (tmp_path / "config.json").write_text("{not json", encoding="utf-8")
    assert levels(doctor.checks())["config.json unreadable"] == "fix"
