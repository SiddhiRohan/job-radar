"""The morning brief: the right picks first, only what changed since the last brief, quiet applications, no crash."""

import json
from datetime import datetime

from radar import applications, brief, mail, watch

DAY = "2026-09-28"


def job(company, req, score, sponsorship="likely", pay=True, title="Data Engineer", days=1, factors=None):
    desc = "Build pipelines." + (" The base salary range is $120,000 - $150,000." if pay else "")
    return {
        "company": company,
        "req_id": req,
        "title": title,
        "url": f"https://example.com/{req}",
        "first_seen": f"{DAY}T08:00:00",
        "posted_days_ago": days,
        "sponsorship": sponsorship,
        "description": desc,
        "verdict": {
            "score_entry": score,
            "score_experienced": score,
            "why": "Strong pipeline work. Gaps are small.",
            "factors": factors or [],
        },
    }


def isolate(tmp_path, monkeypatch):
    monkeypatch.setattr(brief, "STATE", tmp_path / "brief.json")
    monkeypatch.setattr(mail, "STATE", tmp_path / "mail.json")
    monkeypatch.setattr(watch, "STATE", tmp_path / "watch.json")
    monkeypatch.setattr(applications, "PATH", tmp_path / "applications.md")


def test_picks_rank_fit_then_sponsorship_then_pay(tmp_path, monkeypatch):
    isolate(tmp_path, monkeypatch)
    jobs = [
        job("Contoso", "R1", 4, pay=False),
        job("Northwind", "R2", 4),
        job("Fabrikam", "R3", 5),
        job("Tailspin", "R4", 4, sponsorship="no"),  # skipped for sponsorship, never a pick
        job("Woodgrove", "R5", 2),
    ]
    b = brief.build(now=datetime(2026, 9, 28, 9, 0), jobs=jobs)
    assert [p["company"] for p in b["picks"]] == ["Fabrikam", "Northwind", "Contoso"]
    assert b["picks"][1]["pay"] == "$120k to $150k" and b["picks"][0]["reason"] == "Strong pipeline work"


def test_reason_names_the_first_gap(tmp_path, monkeypatch):
    isolate(tmp_path, monkeypatch)
    gap = [
        {
            "factor": "skills",
            "verdict": "partial",
            "posting": "Databricks",
            "resume": "",
            "note": "Missing: Databricks.",
        }
    ]
    b = brief.build(now=datetime(2026, 9, 28, 9, 0), jobs=[job("Contoso", "R1", 4, factors=gap)])
    assert b["picks"][0]["reason"] == "skills: Missing: Databricks."


def test_only_changes_since_the_last_brief(tmp_path, monkeypatch):
    isolate(tmp_path, monkeypatch)
    (tmp_path / "brief.json").write_text(json.dumps({"made_at": "2026-09-27 09:00"}), encoding="utf-8")
    events = [
        {"company": "Contoso", "status": "rejected", "from_status": "applied", "date": "2026-09-26 10:00"},
        {"company": "Northwind", "status": "interview", "from_status": "applied", "date": "2026-09-27 18:30"},
    ]
    (tmp_path / "mail.json").write_text(json.dumps({"events": events}), encoding="utf-8")
    postings = {
        "Fabrikam|R9": {"company": "Fabrikam", "title": "Analyst", "status": "closed", "closed_since": "2026-09-28"},
        "Tailspin|R8": {"company": "Tailspin", "title": "Analyst", "status": "closed", "closed_since": "2026-09-20"},
    }
    (tmp_path / "watch.json").write_text(json.dumps({"postings": postings}), encoding="utf-8")
    b = brief.build(now=datetime(2026, 9, 28, 9, 0), jobs=[])
    assert [x["company"] for x in b["moved"]] == ["Northwind"] and [x["company"] for x in b["closed"]] == ["Fabrikam"]
    assert b["picks"] == [] and "nothing new scored" in brief.text(b)


def test_quiet_applications_after_ten_days(tmp_path, monkeypatch):
    isolate(tmp_path, monkeypatch)
    row = {"company": "Contoso", "title": "Data Engineer", "status": "applied", "folder": "", "req_id": "R1"}
    applications.write(
        [
            row | {"date": "2026-09-10 10:00"},
            row | {"date": "2026-09-25 10:00", "req_id": "R2"},
            row | {"date": "2026-09-01 10:00", "req_id": "R3", "status": "rejected"},
        ]
    )
    (tmp_path / "watch.json").write_text(json.dumps({"postings": {"Contoso|R1": {"status": "open"}}}), encoding="utf-8")
    b = brief.build(now=datetime(2026, 9, 28, 9, 0), jobs=[])
    assert b["quiet"] == [{"company": "Contoso", "title": "Data Engineer", "applied": "2026-09-10", "posting": "open"}]
    assert "Quiet since 2026-09-10: Contoso" in brief.text(b)
