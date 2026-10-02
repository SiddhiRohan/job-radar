"""Skill gaps: names read out of the verdicts' free text, counted once per posting, near misses first."""

from datetime import datetime

from radar import gaps

TODAY = datetime(2026, 10, 1)


def posting(company, score, note="", hard=(), tools=(), seen="2026-09-28"):
    factors = [
        {"factor": f, "verdict": "meets", "posting": "", "resume": "", "note": ""} for f in gaps.fit.MODEL_FACTORS
    ]
    if note:
        factors[2] |= {"verdict": "gap", "note": note}
    verdict = {"factors": factors, "score_entry": score, "score_experienced": score}
    verdict |= {"hard_requirements_missing": list(hard), "platform_tools_missing": list(tools)}
    return {
        "company": company,
        "title": "Data Scientist",
        "req_id": f"R-{company}",
        "url": "",
        "first_seen": seen,
        "verdict": verdict,
    }


def test_skill_names_come_out_of_the_models_sentences():
    assert gaps.terms("GCP/BigQuery (required, in the not-have list).") == ["GCP", "BigQuery"]
    assert gaps.terms("Databricks and Snowflake, both named in the basic qualifications.") == [
        "Databricks",
        "Snowflake",
    ]
    assert gaps.terms("Kubernetes and production-grade observability platforms; no Go") == [
        "Kubernetes",
        "observability platforms",
    ]
    assert gaps.terms("C++ programming") == ["C++"]
    assert gaps.terms("LangChain/LangGraph or equivalent agentic frameworks") == ["LangChain", "LangGraph"]


def test_years_and_long_descriptions_are_not_skills():
    assert gaps.terms("6 years application development experience") == []
    assert gaps.terms("foundational generative model development beyond applied usage") == []


def test_a_skill_counts_once_per_posting_whatever_the_source():
    p = posting("Contoso", 3, note="Missing: Databricks.", hard=["Databricks experience"], tools=["Databricks"])
    r = gaps.analyse([p, posting("Northwind", 4, tools=["Databricks"])], confirmed=[], today=TODAY)
    (g,) = r["skills"]
    assert (g["skill"], g["postings"], g["scored_3"], g["scored_4"], g["not_have"]) == ("Databricks", 2, 1, 1, True)


def test_near_misses_lead_and_one_posting_is_not_a_pattern():
    jobs = [posting("Contoso", 3, note="Missing: Kubernetes."), posting("Northwind", 3, note="Missing: Kubernetes.")]
    jobs += [posting(c, 2, tools=["Azure"]) for c in ("Fabrikam", "Adatum", "Litware")]
    jobs += [posting("Tailspin", 3, note="Missing: Rust.")]
    r = gaps.analyse(jobs, confirmed=[], today=TODAY)
    assert [g["skill"] for g in r["skills"]] == ["Kubernetes", "Azure"]


def test_aliases_and_case_count_as_one_skill_and_generic_words_drop():
    jobs = [posting("Contoso", 2, tools=["Google Cloud"]), posting("Northwind", 2, hard=["gcp"])]
    jobs += [posting("Fabrikam", 2, note="Missing: ML and AI."), posting("Adatum", 2, note="Missing: ML.")]
    (g,) = gaps.analyse(jobs, confirmed=[], today=TODAY)["skills"]
    assert (g["skill"], g["postings"]) == ("Google Cloud", 2)


def test_a_confirmed_skill_is_a_resume_fix_not_a_course():
    jobs = [posting("Contoso", 3, note="Missing: Spark."), posting("Northwind", 3, note="Missing: Spark.")]
    r = gaps.analyse(jobs, confirmed=["spark"], today=TODAY)
    assert [g["skill"] for g in r["confirmed"]] == ["Spark"]
    lines = gaps.summary(r)
    assert lines[-1] == "You confirmed Spark, yet 2 postings could not find it: show it on your resume."
    assert not any(line.startswith("Spark: missing") for line in lines)


def test_postings_before_the_window_do_not_count():
    jobs = [posting(c, 3, note="Missing: Kubernetes.", seen="2026-08-01") for c in ("Contoso", "Northwind")]
    r = gaps.analyse(jobs, confirmed=[], today=TODAY)
    assert r["skills"] == [] and r["postings"] == 0
    assert gaps.summary(r) == ["No skill is missing from two or more of the 0 postings scored since 2026-09-01."]


def test_names_with_a_slash_ampersand_or_digit_stay_whole():
    assert gaps.terms("A/B testing and experimentation") == ["A/B testing", "experimentation"]
    assert gaps.terms("CI/CD, PL/SQL and R&D") == ["CI/CD", "PL/SQL", "R&D"]
    assert gaps.terms("S3, EC2 and D3.js") == ["S3", "EC2", "D3.js"]
    assert gaps.terms("AWS/GCP/Azure") == ["AWS", "GCP", "Azure"]  # three long names are three skills
    assert gaps.terms("4+ years of AI/ML") == []
