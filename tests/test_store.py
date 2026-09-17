"""Overlapping runs must never store a posting twice or lose a row."""

import json

from radar import store


def use_tmp(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "JOBS", tmp_path / "jobs.jsonl")
    monkeypatch.setattr(store, "SEEN", tmp_path / "seen.json")
    monkeypatch.setattr(store, "LOCK", tmp_path / "jobs.lock")


def row(req, **kw):
    return {"company": "GM", "req_id": req, "title": "Data Engineer", **kw}


def test_second_run_adds_nothing(tmp_path, monkeypatch):
    use_tmp(tmp_path, monkeypatch)
    assert len(store.append_new([row("R1"), row("R2")], ["GM|R1", "GM|R2"])) == 2
    assert store.append_new([row("R1"), row("R2"), row("R3")], ["GM|R3"]) == [row("R3")]
    assert len(store.load()) == 3
    assert set(json.loads(store.SEEN.read_text())) == {"GM|R1", "GM|R2", "GM|R3"}


def test_dedupe_prefers_scored_copy_and_first_seen():
    a = row("R1", first_seen="t1")
    b = row("R1", first_seen="t2", verdict={"score_entry": 4})
    out = store.dedupe([a, b])
    assert len(out) == 1 and out[0]["verdict"]["score_entry"] == 4 and out[0]["first_seen"] == "t1"


def test_save_keeps_rows_appended_meanwhile(tmp_path, monkeypatch):
    use_tmp(tmp_path, monkeypatch)
    store.append_new([row("R1")])
    mine = store.load()
    store.append_new([row("R2")])  # another run lands while the scorer is working
    mine[0]["verdict"] = {"score_entry": 3}
    merged = store.save(mine)
    assert {store.key(j) for j in merged} == {"GM|R1", "GM|R2"}
    assert store.load()[0]["verdict"]["score_entry"] == 3
