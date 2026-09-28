"""Terminal commands a person or a coding assistant uses: evaluate one posting, and record applications."""

from radar import applications, evaluate

JOB = {
    "company": "Contoso",
    "title": "Data Engineer",
    "location": "Remote",
    "req_id": "R-12345",
    "url": "https://contoso.wd5.myworkdayjobs.com/en-US/Careers/job/Remote/Data-Engineer_R-12345",
    "sponsorship": "likely",
    "sponsorship_evidence": None,
    "years_required": 3,
    "description": "Build pipelines. The base salary range is $120,000 - $150,000.",
    "verdict": {
        "score_entry": 3,
        "score_experienced": 4,
        "recommended_resume": "experienced",
        "hard_requirements_missing": ["Databricks"],
        "why": "Pipelines and Spark match; Databricks is the gap.",
    },
}


def test_summary_reads_like_a_verdict():
    text = "\n".join(evaluate.summary(JOB))
    assert "Contoso | Data Engineer | Remote | R-12345" in text
    assert "fit: entry 3 / experienced 4, use the experienced resume" in text
    assert "years asked: 3 | pay: $120k to $150k" in text and "missing: Databricks" in text


def test_a_link_that_is_not_workday_is_explained(capsys):
    assert evaluate.main(["https://example.com/jobs/1"]) == 1
    assert "not a Workday job URL" in capsys.readouterr().out
    assert evaluate.main([]) == 2


def test_add_list_and_status_from_the_terminal(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(applications, "PATH", tmp_path / "applications.md")
    assert applications.main(["add", "Contoso", "R-12345", "Data Engineer"]) == 0
    assert applications.add("Contoso", "R-12345", "Data Engineer") is False  # already recorded
    assert applications.main(["status", "Contoso", "R-12345", "interview"]) == 0
    assert applications.main(["status", "Contoso", "R-12345", "hired"]) == 1
    capsys.readouterr()
    applications.main(["list", "interview"])
    out = capsys.readouterr().out
    assert "interview  Contoso | Data Engineer | R-12345" in out and "1 application(s)" in out


def test_a_stored_posting_is_found_by_company_and_id(tmp_path, monkeypatch, capsys):
    import json

    monkeypatch.chdir(tmp_path)
    (tmp_path / "jobs.jsonl").write_text(json.dumps(JOB) + "\n", encoding="utf-8")
    assert evaluate.main(["contoso", "R-12345"]) == 0 and "fit: entry 3" in capsys.readouterr().out
    assert evaluate.main(["Contoso", "R-99999"]) == 1 and "paste its link" in capsys.readouterr().out
