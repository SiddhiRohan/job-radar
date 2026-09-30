"""A pasted Greenhouse, Lever or Ashby link is found on its board, scored and stored like a Workday one."""

import json

from radar import boards, evaluate, score

BOARD = {"name": "Contoso", "ats": "greenhouse", "board": "contoso", "sponsors_h1b": True, "tier": 2}
JOB = {"company": "Contoso", "req_id": "4001", "title": "Data Engineer", "description": "Build pipelines with Spark."}


def listed(*ids, title="Data Engineer"):
    return [{"req_id": i, "detail": {"title": title, "description": "Build pipelines with Spark."}} for i in ids]


def test_a_pasted_board_link_is_found_scored_and_stored(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "companies.json").write_text(json.dumps([BOARD]), encoding="utf-8")
    (tmp_path / "config.json").write_text(json.dumps({"us_only": True}), encoding="utf-8")
    posting = {
        "company": "Contoso",
        "title": "Data Engineer",
        "location": "Seattle, WA",
        "posted_on": "Posted Today",
        "posted_days_ago": 0,
        "req_id": "4001",
        "url": "https://job-boards.greenhouse.io/contoso/jobs/4001",
        "ats": "greenhouse",
        "detail": {
            "description": "Build pipelines. The base salary range is $120,000 - $150,000.",
            "title": "Data Engineer",
            "location": "Seattle, WA",
            "additional_locations": [],
            "country": None,
            "country_code": None,
            "time_type": None,
            "non_us": False,
        },
    }
    monkeypatch.setattr(boards, "fetch", lambda company: [dict(posting)])
    monkeypatch.setattr(score, "load_api_key", lambda: "sk-test")
    monkeypatch.setattr(score, "system_blocks", lambda: [])
    monkeypatch.setattr(score, "ask_claude", lambda key, blocks, j: ({"score_entry": 3, "score_experienced": 4}, "m"))
    j = evaluate.ingest_url("https://job-boards.greenhouse.io/contoso/jobs/4001?gh_src=abc")
    assert j["company"] == "Contoso" and j["verdict"]["score_experienced"] == 4 and j["sponsorship"]
    assert "detail" not in j and (tmp_path / "jobs.jsonl").read_text(encoding="utf-8").count("4001") >= 1
    again = evaluate.ingest_url("https://boards.greenhouse.io/contoso/jobs/4001")
    assert again["req_id"] == "4001"  # stored now: no second score
