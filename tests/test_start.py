"""start.py names the cause when setup stops and leaves no half-made .venv behind. Offline: nothing is installed."""

import pytest

import start


def use_venv(monkeypatch, venv):
    monkeypatch.setattr(start, "VENV", venv)
    monkeypatch.setattr(start, "PY", venv / "bin" / "python")
    monkeypatch.setattr(start, "STAMP", venv / ".requirements.sha256")


def test_a_venv_that_could_not_be_made_is_removed_and_named(tmp_path, monkeypatch):
    venv = tmp_path / ".venv"
    use_venv(monkeypatch, venv)

    def call(args, **kw):
        (venv / "bin").mkdir(parents=True)  # without ensurepip, venv stops after making the folder
        (venv / "bin" / "python").write_text("", encoding="utf-8")
        return 1

    monkeypatch.setattr(start.subprocess, "call", call)
    with pytest.raises(OSError, match="python3-venv"):
        start.prepare()
    assert not venv.exists()  # the next start makes it again instead of taking it for a ready one


def test_packages_that_did_not_install_are_tried_again_next_start(tmp_path, monkeypatch):
    venv = tmp_path / ".venv"
    (venv / "bin").mkdir(parents=True)
    (venv / "bin" / "python").write_text("", encoding="utf-8")
    use_venv(monkeypatch, venv)
    monkeypatch.setattr(start.subprocess, "call", lambda args, **kw: 1)
    with pytest.raises(OSError, match="internet connection"):
        start.prepare()
    assert not (venv / ".requirements.sha256").exists()
