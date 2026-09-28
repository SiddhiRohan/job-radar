"""Batch scoring: one batch for the run's postings, anything it does not answer is asked directly. Offline: the HTTP
calls are replaced, sockets refuse, and the clock is fake so the hour-long wait takes no time."""

import json
import socket
from unittest.mock import Mock

import pytest

from radar import batch, score

VERDICT = {"factors": [], "score_entry": 4, "score_experienced": 3, "why": "Synthetic."}


class Reply:
    def __init__(self, data=None, text="", status_code=200):
        self.data, self.text, self.status_code = data, text, status_code

    def json(self):
        return self.data

    def raise_for_status(self):
        if self.status_code != 200:
            raise batch.requests.HTTPError(str(self.status_code))


def line(cid, kind, text=None, stop="end_turn"):
    result = {"type": kind}
    if kind == "succeeded":
        content = [{"type": "text", "text": text if text is not None else json.dumps(VERDICT)}]
        result["message"] = {"model": "claude-sonnet-4-6", "stop_reason": stop, "content": content}
    return json.dumps({"custom_id": cid, "result": result})


class Api:
    """The batch endpoints: statuses are served in order, the last one repeating; posts are recorded."""

    def __init__(self, statuses, results="", create=None):
        self.statuses, self.results, self.posts = list(statuses), results, []
        self.create = create or Reply({"id": "msgbatch_1", "processing_status": "in_progress"})

    def post(self, url, **kw):
        self.posts.append((url, kw.get("json")))
        return self.create if url == batch.URL else Reply({"processing_status": "canceling"})

    def get(self, url, **kw):
        if url.endswith("/results"):
            return Reply(text=self.results)
        state = self.statuses.pop(0) if len(self.statuses) > 1 else self.statuses[0]
        return Reply({"processing_status": state, "results_url": batch.URL + "/msgbatch_1/results"})


@pytest.fixture
def api(monkeypatch):
    monkeypatch.setattr(socket.socket, "connect", Mock(side_effect=AssertionError("network forbidden")))

    def use(fake):
        monkeypatch.setattr(batch.requests, "post", fake.post)
        monkeypatch.setattr(batch.requests, "get", fake.get)
        return fake

    return use


def clock(step):
    t = iter(range(0, 10**7, step))
    return lambda: next(t)


def test_a_batch_names_requests_by_position_and_reads_back_the_verdicts(api):
    results = "\n".join([line("p0", "succeeded"), line("p1", "errored"), line("p2", "expired"), ""])
    fake = api(Api(["in_progress", "in_progress", "ended"], results))
    got = batch.score("test-key", [{"n": 0}, {"n": 1}, {"n": 2}], sleep=lambda s: None, clock=clock(30))
    assert got == {0: (VERDICT, "claude-sonnet-4-6")}  # errored and expired requests are asked directly later
    sent = fake.posts[0][1]["requests"]
    assert [r["custom_id"] for r in sent] == ["p0", "p1", "p2"] and sent[1]["params"] == {"n": 1}


def test_a_refusal_is_kept_and_a_cut_off_verdict_is_asked_again(api):
    api(Api(["ended"], "\n".join([line("p0", "succeeded", stop="refusal"), line("p1", "succeeded", text='{"a": 4')])))
    got = batch.answers("test-key", {"results_url": batch.URL + "/msgbatch_1/results"})
    assert got == {0: ({"error": "refusal"}, "claude-sonnet-4-6")}


def test_a_batch_past_the_wait_is_cancelled_and_what_finished_is_kept(api):
    minutes = batch.WAIT_SECONDS // batch.POLL_SECONDS
    fake = api(Api(["in_progress"] * (minutes + 2) + ["ended"], line("p1", "succeeded")))
    got = batch.score("test-key", [{"n": 0}, {"n": 1}], sleep=lambda s: None, clock=clock(batch.POLL_SECONDS))
    assert fake.posts[-1][0] == batch.URL + "/msgbatch_1/cancel"
    assert got == {1: (VERDICT, "claude-sonnet-4-6")}


def test_a_batch_that_cannot_be_sent_leaves_every_posting_to_direct_calls(api):
    api(Api(["ended"], create=Reply(text="overloaded", status_code=529)))
    assert batch.score("test-key", [{"n": 0}], sleep=lambda s: None, clock=clock(1)) == {}


def run_score(tmp_path, monkeypatch, cfg, batched):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "config.json").write_text(json.dumps(cfg), encoding="utf-8")
    jobs = [
        {"company": c, "title": "Data Engineer", "location": "Austin, TX", "posted_days_ago": 0, "req_id": c}
        for c in ("Contoso", "Northwind")
    ]
    monkeypatch.setattr(score.store, "load", lambda: jobs)
    monkeypatch.setattr(score, "load_api_key", lambda: "test-key")
    monkeypatch.setattr(score, "system_blocks", lambda: [{"type": "text", "text": "rules"}])
    send = Mock(return_value=batched)
    monkeypatch.setattr(score.batch, "score", send)
    direct = Mock(return_value=({**VERDICT, "why": "direct"}, "claude-sonnet-5"))
    monkeypatch.setattr(score, "ask_claude", direct)
    score.main()
    stored = [json.loads(x) for x in (tmp_path / "jobs.jsonl").read_text(encoding="utf-8").splitlines()]
    return send, direct, stored


def test_the_run_asks_directly_about_what_the_batch_left(tmp_path, monkeypatch):
    send, direct, stored = run_score(tmp_path, monkeypatch, {"score_batch": True}, {0: (VERDICT, "claude-sonnet-4-6")})
    bodies = send.call_args.args[1]
    assert len(bodies) == 2 and bodies[0]["output_config"]["format"]["schema"] == score.fit.SCHEMA
    assert stored[0]["verdict"] == VERDICT and stored[0]["scored_with"] == "claude-sonnet-4-6"
    assert direct.call_count == 1 and stored[1]["verdict"]["why"] == "direct"


def test_without_the_setting_no_batch_is_sent(tmp_path, monkeypatch):
    send, direct, stored = run_score(tmp_path, monkeypatch, {}, {})
    assert send.call_count == 0 and direct.call_count == 2


def test_a_posting_stored_during_the_wait_survives_the_save(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "config.json").write_text(json.dumps({"score_batch": True}), encoding="utf-8")
    first = {
        "company": "Contoso",
        "title": "Data Engineer",
        "location": "Austin, TX",
        "posted_days_ago": 0,
        "req_id": "R1",
    }
    score.store.JOBS.write_text(json.dumps(first) + "\n", encoding="utf-8")
    pasted = first | {"company": "Northwind", "req_id": "R2", "verdict": VERDICT}

    def slow_batch(api_key, bodies):
        score.store.append_new([pasted])  # someone pastes a link in the app while the batch runs
        return {}

    monkeypatch.setattr(score, "load_api_key", lambda: "test-key")
    monkeypatch.setattr(score, "system_blocks", lambda: [{"type": "text", "text": "rules"}])
    monkeypatch.setattr(score.batch, "score", slow_batch)
    monkeypatch.setattr(score, "ask_claude", lambda api_key, system, job: (VERDICT, "claude-sonnet-5"))
    score.main()
    rows = {j["req_id"]: j for j in score.store.load()}
    assert set(rows) == {"R1", "R2"} and rows["R1"]["verdict"] == VERDICT
