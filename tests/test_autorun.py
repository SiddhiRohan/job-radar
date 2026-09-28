"""The run lock and the daily run while the web app is open: one run at a time, catch-up, no retry storm."""

import json
import os
import time
from datetime import datetime, timedelta

import run
from radar import autorun, chat, runlock

CFG = {"auto_run": True, "run_time": "07:30"}


def lock_here(tmp_path, monkeypatch):
    monkeypatch.setattr(runlock, "LOCK", tmp_path / "run.lock")


def test_lock_refuses_a_second_run_and_takes_over_a_stale_one(tmp_path, monkeypatch):
    lock_here(tmp_path, monkeypatch)
    assert runlock.acquire() and runlock.held() and not runlock.acquire()
    assert len(runlock.since()) == 5  # HH:MM
    old = time.time() - runlock.STALE_SECONDS - 60
    os.utime(runlock.LOCK, (old, old))
    assert not runlock.held() and runlock.acquire()
    runlock.release()
    assert not runlock.LOCK.exists() and runlock.since() == ""


def test_run_py_steps_aside_when_another_run_holds_the_lock(tmp_path, monkeypatch, capsys):
    lock_here(tmp_path, monkeypatch)
    ran = []
    monkeypatch.setattr(run, "step", lambda name, args: ran.append(name) or 0)
    monkeypatch.setattr("sys.argv", ["run.py"])
    runlock.acquire()
    run.main()
    assert ran == [] and "not starting a second one" in capsys.readouterr().out
    runlock.release()
    run.main()
    assert ran[0] == "radar.poll" and not runlock.LOCK.exists()  # released after the steps


def test_run_button_reports_an_outside_run(tmp_path, monkeypatch):
    lock_here(tmp_path, monkeypatch)
    monkeypatch.setitem(chat.RUN, "proc", None)
    runlock.acquire()
    r = chat.run_radar(1)
    assert r["started"] is False and "still going" in r["reason"]
    assert chat.run_status()["running"] is True
    runlock.release()


def test_due_after_run_time_unless_already_run_today():
    today_0800 = datetime(2026, 9, 28, 8, 0)
    assert autorun.due(today_0800, CFG, datetime(2026, 9, 27, 7, 35))  # yesterday's run: catch up
    assert not autorun.due(today_0800, CFG, datetime(2026, 9, 28, 7, 31))  # already ran this morning
    assert not autorun.due(datetime(2026, 9, 28, 6, 0), CFG, None)  # before run time
    assert autorun.due(today_0800, CFG, datetime(2026, 9, 28, 6, 0))  # a manual run before 7:30 does not count
    assert not autorun.due(today_0800, {"auto_run": False}, None)


def test_a_failed_trigger_waits_two_hours(tmp_path):
    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps(CFG), encoding="utf-8")
    calls, state, now = [], {}, datetime(2026, 9, 28, 9, 0)

    def tick(t):
        return autorun.check(lambda: calls.append(t) or "started", state, now=t, cfg_path=cfg, last=lambda: None)

    assert tick(now) == "started" and tick(now + timedelta(minutes=5)) is None
    assert tick(now + timedelta(hours=2, minutes=1)) == "started" and len(calls) == 2


def test_last_ran_reads_utc_and_tolerates_a_missing_file(tmp_path):
    p = tmp_path / "last_run.json"
    assert autorun.last_ran(p) is None
    p.write_text(json.dumps({"ran_at": "2026-09-28T11:30:00+00:00"}), encoding="utf-8")
    assert autorun.last_ran(p).tzinfo is None
