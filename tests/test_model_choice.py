"""The model comes from ANTHROPIC_MODEL in the environment or in .env, and scoring uses the same choice."""

import importlib

from radar import llm


def test_env_file_picks_the_model(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("ANTHROPIC_MODEL", raising=False)
    (tmp_path / ".env").write_text("ANTHROPIC_MODEL=claude-sonnet-5\n", encoding="utf-8")
    try:
        assert importlib.reload(llm).MODELS[0] == "claude-sonnet-5"
        monkeypatch.setenv("ANTHROPIC_MODEL", "claude-opus-5")
        assert importlib.reload(llm).MODELS[0] == "claude-opus-5"  # the environment wins over .env
    finally:
        monkeypatch.undo()
        importlib.reload(llm)
