"""The scorer sends the prompt and schema from radar/fit.py. Offline: the HTTP call is replaced and sockets refuse."""

import json
import socket
from unittest.mock import Mock

from radar import fit, score

VERDICT = {"factors": [], "score_entry": 3, "score_experienced": 2, "why": "Synthetic."}


class Reply:
    status_code = 200
    text = ""

    def json(self):
        return {"stop_reason": "end_turn", "content": [{"type": "text", "text": json.dumps(VERDICT)}]}


def test_system_prompt_starts_with_the_fit_rules(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "profile.md").write_text("Synthetic profile", encoding="utf-8")
    monkeypatch.setattr(score.resumes, "role_status", lambda: {"DS and DE Resumes": {"one-page": True}})
    monkeypatch.setattr(score.resumes, "bases", lambda: {"entry": "ENTRY", "experienced": "EXPERIENCED"})
    blocks = score.system_blocks()
    assert blocks[0]["text"].startswith(fit.RULES + "\n\nCANDIDATE PROFILE:\nSynthetic profile")
    assert blocks[-1]["cache_control"] == {"type": "ephemeral"}  # rules and resumes stay one cached prefix


def test_request_carries_the_schema_and_room_for_the_factors(monkeypatch):
    monkeypatch.setattr(socket.socket, "connect", Mock(side_effect=AssertionError("network forbidden")))
    post = Mock(return_value=Reply())
    monkeypatch.setattr(score.requests, "post", post)
    job = {"title": "Data Engineer", "company": "GM", "location": "Austin, TX", "description": "Build pipelines."}
    verdict, model = score.ask_claude("test-key", [{"type": "text", "text": "rules"}], job)
    body = post.call_args.kwargs["json"]
    assert body["output_config"] == {"format": {"type": "json_schema", "schema": fit.SCHEMA}}
    assert body["max_tokens"] >= 1536  # the four factors add a few hundred output tokens to every verdict
    assert verdict == VERDICT and model == score.MODELS[0]
