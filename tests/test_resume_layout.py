"""Resume layouts: one resume.docx, an entry and an experienced file, or the original folder tree."""

import pytest
from docx import Document

from tailoring import apply, resumes


def make_docx(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = Document()
    doc.add_paragraph(text)
    doc.save(path)


def test_one_resume_serves_as_both_bases(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    make_docx(tmp_path / "Resume" / "resume.docx", "Data engineer, 3 years of Spark")
    (tmp_path / "Resume" / "~$resume.docx").write_bytes(b"lock file Word leaves behind")
    paths = resumes.base_paths()
    assert paths["entry"] == paths["experienced"] and paths["entry"].name == "resume.docx"
    assert "Spark" in resumes.bases()["experienced"] and not resumes.legacy()


def test_entry_and_experienced_files(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    make_docx(tmp_path / "Resume" / "Entry resume.docx", "junior")
    make_docx(tmp_path / "Resume" / "experienced.docx", "senior")
    b = resumes.bases()
    assert b["entry"].strip() == "junior" and b["experienced"].strip() == "senior"


def test_plain_text_resume_scores_but_cannot_be_tailored(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "Resume").mkdir()
    (tmp_path / "Resume" / "resume.txt").write_text("Analyst, SQL and Tableau", encoding="utf-8")
    assert "Tableau" in resumes.bases()["entry"]
    with pytest.raises(RuntimeError, match="Word resume"):
        apply.pick_base({"verdict": {"recommended_resume": "entry"}})


def test_simple_layout_tailors_from_the_recommended_base(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    make_docx(tmp_path / "Resume" / "entry.docx", "junior")
    make_docx(tmp_path / "Resume" / "experienced.docx", "senior")
    path, label = apply.pick_base({"verdict": {"recommended_resume": "entry"}})
    assert path.name == "entry.docx" and label == "entry"


def test_no_resume_and_no_profile_are_explained(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert resumes.base_paths() == {} and resumes.role_folders() == [] and resumes.tailored_folders() == []
    with pytest.raises(FileNotFoundError, match="resume.docx"):
        resumes.bases()
    assert resumes.profile_text() == resumes.NO_PROFILE


def test_original_layout_wins_when_present(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    make_docx(tmp_path / resumes.ENTRY_BASE, "entry base")
    make_docx(tmp_path / resumes.EXPERIENCED_BASE, "experienced base")
    make_docx(tmp_path / "Resume" / "resume.docx", "loose file")
    assert resumes.legacy() and resumes.bases()["experienced"].strip() == "experienced base"
