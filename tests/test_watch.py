"""Posting drift: closed, retitled, repriced and rewritten postings are recorded once with the date first seen."""

import json

import requests

from radar import applications, store, watch

APP = {
    "date": "2026-09-20 10:00",
    "company": "GM",
    "title": "Data Engineer",
    "status": "applied",
    "folder": "",
    "req_id": "R1",
}
JOB = {
    "company": "GM",
    "req_id": "R1",
    "title": "Data Engineer",
    "detail_path": "/job/x",
    "url": "u",
    "first_seen": "2026-09-20T10:00:00",
    "description": "Build pipelines with Spark. The base salary range is $120,000 - $150,000. Apply by Friday 12 September.",
}
COMPANY = {"name": "GM", "tenant": "generalmotors", "shard": "wd5", "site": "Careers_GM"}


def http_error(code, body=b""):
    r = requests.Response()
    r.status_code = code
    r._content = body
    return requests.HTTPError(response=r)


def test_closed_when_the_record_is_gone():
    def gone(*a):
        raise http_error(404)

    assert watch.check(APP, JOB, COMPANY, gone)["status"] == "closed"


def test_workday_permission_denied_means_taken_down_but_a_bare_403_does_not():
    def taken_down(*a):
        raise http_error(403, b'{"errorCode":"S22","httpStatus":403,"message":"permission denied"}')

    def blocked(*a):
        raise http_error(403, b"<html>Access denied</html>")

    assert watch.check(APP, JOB, COMPANY, taken_down)["status"] == "closed"
    assert watch.check(APP, JOB, COMPANY, blocked)["status"] == "unknown"


def test_transient_error_is_unknown_not_closed():
    def flaky(*a):
        raise http_error(503)

    r = watch.check(APP, JOB, COMPANY, flaky)
    assert r["status"] == "unknown" and "503" in r["note"]


def test_changes_are_named_and_digits_do_not_count():
    same = {
        "title": "Data Engineer",
        "description": "Build pipelines with Spark. The base salary range is $120,000 - $150,000. Apply by Friday 19 September.",
    }
    assert watch.compare(JOB, same) == []
    changed = {
        "title": "Senior Data Engineer",
        "description": "Build pipelines with Spark. The base salary range is $130,000 - $160,000. Apply by Friday.",
    }
    assert watch.compare(JOB, changed) == [
        "title now: Senior Data Engineer",
        "pay now: $130k to $160k (was $120k to $150k)",
    ]
    rewritten = {
        "title": "Data Engineer",
        "description": "An entirely different role: forecast demand with statistical models and dashboards.",
    }
    assert "description rewritten" in watch.compare(JOB, rewritten)


def test_run_records_first_seen_and_skips_finished(tmp_path, monkeypatch):
    monkeypatch.setattr(applications, "PATH", tmp_path / "applications.md")
    monkeypatch.setattr(watch, "STATE", tmp_path / "watch.json")
    monkeypatch.setattr(store, "load", lambda: [JOB, dict(JOB, req_id="R2", title="Analyst")])
    monkeypatch.chdir(tmp_path)
    (tmp_path / "companies.json").write_text(json.dumps([COMPANY]), encoding="utf-8")
    applications.write([APP, dict(APP, req_id="R2", title="Analyst", status="rejected")])
    calls = []

    def fetch(tenant, shard, path):
        calls.append(path)
        raise http_error(404)

    counts = watch.run(fetch)
    assert counts == {"open": 0, "closed": 1, "changed": 0, "unknown": 0} and calls == [
        "/job/x"
    ]  # rejected one skipped
    rep = watch.report()
    assert rep["closed"][0]["key"] == "GM|R1" and rep["closed"][0]["closed_since"]
    first = rep["closed"][0]["closed_since"]
    watch.run(fetch)
    assert watch.report()["closed"][0]["closed_since"] == first  # not reset on the next run
