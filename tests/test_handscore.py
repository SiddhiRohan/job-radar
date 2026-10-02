"""Scoring with a coding assistant: the packet it reads, and the checks a verdict passes before it is stored."""

import json

import pytest

from radar import fit, handscore, store


def factor(name, verdict="meets"):
    return {"factor": name, "verdict": verdict, "posting": "asks", "resume": "shows", "note": ""}


def good():
    return {
        "factors": [factor(n) for n in fit.MODEL_FACTORS],
        "score_entry": 3,
        "score_experienced": 4,
        "recommended_resume": "experienced",
        "recommended_variant": "",
        "years_required": 3,
        "hard_requirements_missing": [],
        "platform_tools_missing": [],
        "sponsorship": "unknown",
        "sponsorship_evidence": None,
        "cover_letter_required": False,
        "why": "Pipelines match; the domain is new.",
        "apply": True,
    }


def posting(company, req, title="Data Engineer", days=0, **extra):
    return {
        "company": company,
        "req_id": req,
        "title": title,
        "location": "Austin, TX",
        "posted_days_ago": days,
    } | extra


def test_a_complete_verdict_passes():
    assert handscore.check(good()) == []


@pytest.mark.parametrize(
    "change, problem",
    [
        ({"score_entry": 6}, "verdict.score_entry should be one of 1, 2, 3, 4, 5"),
        ({"score_entry": True}, "verdict.score_entry should be integer"),
        ({"apply": "yes"}, "verdict.apply should be boolean"),
        ({"mood": "great"}, "verdict.mood is not in the schema"),
        ({"factors": [factor("skills", "strong")]}, "verdict.factors.0.verdict should be one of meets, partial, gap"),
    ],
)
def test_a_verdict_off_the_schema_says_what_is_wrong(change, problem):
    assert problem in handscore.check(good() | change)


def test_missing_fields_and_factor_order_are_caught():
    v = good()
    del v["why"]
    assert handscore.check(v) == ["verdict.why is missing"]
    swapped = good() | {"factors": [factor(n) for n in reversed(fit.MODEL_FACTORS)]}
    assert "in that order" in handscore.check(swapped)[0]


def test_next_writes_the_postings_a_run_would_score_first(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(handscore.resumes, "bases", lambda: {"entry": "ENTRY", "experienced": "EXPERIENCED"})
    jobs = [
        posting("Contoso", "R1", days=0),
        posting("Northwind", "R2", title="Junior Data Engineer", days=3),
        posting("Fabrikam", "R3", years_gate=True, years_required=8),  # a rule decides it: left to the run
        posting("Adatum", "R4", verdict={"score_entry": 2}),  # scored already
    ]
    assert handscore.next_batch(10, jobs) == ["Northwind|R2", "Contoso|R1"]  # entry-level first
    packet = json.loads((tmp_path / ".cache" / "to_score.json").read_text(encoding="utf-8"))
    assert packet["rules"] == fit.RULES and packet["schema"] == fit.SCHEMA and packet["entry_resume"] == "ENTRY"
    assert [p["id"] for p in packet["postings"]] == ["Northwind|R2", "Contoso|R1"]


def test_save_stores_good_verdicts_and_names_the_rest(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    jobs = [posting("Contoso", "R1"), posting("Northwind", "R2")]
    store.JOBS.write_text("".join(json.dumps(j) + "\n" for j in jobs), encoding="utf-8")
    verdicts = {"Contoso|R1": good(), "Northwind|R2": good() | {"score_entry": 9}, "Nobody|R9": good()}
    stored, rejected = handscore.save(verdicts)
    assert stored == ["Contoso|R1"] and set(rejected) == {"Northwind|R2", "Nobody|R9"}
    rows = {store.key(j): j for j in store.load()}
    assert rows["Contoso|R1"]["scored_with"] == "assistant" and rows["Contoso|R1"]["verdict"]["score_experienced"] == 4
    assert "verdict" not in rows["Northwind|R2"]
    with pytest.raises(ValueError, match="one JSON object"):
        handscore.save([good()])
