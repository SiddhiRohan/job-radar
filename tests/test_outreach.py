"""Offline outreach routes: synthetic inputs, controlled threads, no HTTP client."""

import importlib
import io
import socket
import sys
from unittest.mock import Mock

import pytest


@pytest.fixture
def server(monkeypatch):
    # Legacy CLI imports reconfigure stdout; leave pytest's capture stream alone.
    with monkeypatch.context() as patch:
        patch.setattr(sys, "stdout", io.TextIOWrapper(io.BytesIO(), encoding="utf-8"))
        module = importlib.import_module("server")
    monkeypatch.setattr(socket.socket, "connect", Mock(side_effect=AssertionError("network forbidden")))
    monkeypatch.setattr(module.letters, "outreach", Mock(side_effect=AssertionError("mock the generator")))
    monkeypatch.setattr(module, "JOBS", {})

    class InlineThread:
        def __init__(self, target, daemon):
            self.target = target

        def start(self):
            self.target()

    monkeypatch.setattr(module.threading, "Thread", InlineThread)
    return module


@pytest.mark.parametrize("description", [None, "Synthetic description"])
def test_generation_uses_edited_sections(server, monkeypatch, tmp_path, description):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "profile.md").write_text("Synthetic profile", encoding="utf-8")
    job = {"company": "Example", "req_id": "R7"}
    if description is not None:
        job["description"] = description
    find = Mock(return_value=job)
    monkeypatch.setattr(server.applier, "find_job", find)
    result = {"linkedin_note": "Synthetic note", "message": "word " * 100}
    generate = Mock(return_value=result)
    monkeypatch.setattr(server.letters, "outreach", generate)
    response = server.start_outreach(
        {
            "company": "Example",
            "req_id": "R7",
            "sections": [{"text": ["Edited summary"]}, {"text": ["Edited first", "Edited second"]}],
        }
    )
    assert server.job_status(response["job_id"]) == {"status": "done", "result": result}
    find.assert_called_once_with("Example", "R7")
    generate.assert_called_once_with(
        job, description or "", "Synthetic profile", "Edited summary\nEdited first\nEdited second"
    )


def test_generation_failure_is_failed_background_job(server, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "profile.md").write_text("Synthetic profile", encoding="utf-8")
    monkeypatch.setattr(server.applier, "find_job", Mock(return_value={}))
    monkeypatch.setattr(server.letters, "outreach", Mock(side_effect=RuntimeError("synthetic failure")))
    response = server.start_outreach({"company": "Example", "req_id": "R7", "sections": []})
    status = server.job_status(response["job_id"])
    assert status["status"] == "error"
    assert "RuntimeError: synthetic failure" in status["error"]


@pytest.mark.parametrize("with_outreach", [False, True])
def test_save_preserves_files_and_latest_edits(server, tmp_path, with_outreach):
    source, dest = tmp_path / "build", tmp_path / "saved"
    source.mkdir()
    (source / "resume.docx").write_bytes(b"synthetic resume")
    (source / "jd.txt").write_text("Synthetic JD", encoding="utf-8")
    body = {
        "dir": str(source),
        "dest": str(dest),
        "job": {"company": "Example", "req_id": "R7", "title": "Engineer", "url": "https://example.invalid"},
        "assessment": ["Synthetic fit"],
        "notes": ["Synthetic question"],
    }
    if with_outreach:
        body["outreach"] = {"linkedin_note": "Initial", "message": "initial message"}
        server.save_folder(body)
        # Deliberate out-of-range edits must still save without a rebuild.
        body["outreach"] = {"linkedin_note": "x" * 300, "message": "latest\tedit\nthree  four"}
    assert server.save_folder(body) == {"folder": str(dest)}
    assert (dest / "resume.docx").read_bytes() == b"synthetic resume"
    assert (dest / "jd.txt").read_text(encoding="utf-8") == "Synthetic JD"
    notes = (dest / "notes.md").read_text(encoding="utf-8")
    assert "Synthetic fit" in notes and "Synthetic question" in notes
    if with_outreach:
        text = (dest / "outreach.md").read_text(encoding="utf-8")
        assert "LinkedIn note (300 characters" in text
        assert "Outreach message (4 words" in text
        assert body["outreach"]["linkedin_note"] in text
        assert body["outreach"]["message"] in text
        assert "Initial" not in text
    else:
        assert not (dest / "outreach.md").exists()
