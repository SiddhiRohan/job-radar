"""Apply and Entry level rows in the digest name the factors that are partial or a gap; nothing else changes."""

from radar import digest, fit

DAY = "2026-09-27T07:30:00+00:00"


def factors(**verdicts):
    notes = {"skills": "Missing: Databricks."}
    return [
        {"factor": n, "verdict": verdicts.get(n, "meets"), "posting": "ask", "resume": "", "note": notes.get(n, "")}
        for n in fit.MODEL_FACTORS
    ]


def job(title, best, sponsorship="likely", **verdict):
    v = {"score_entry": best, "score_experienced": best, "why": f"Why {title}.", **verdict}
    return {
        "company": "GM",
        "req_id": title[:8],
        "title": title,
        "location": "Austin, TX",
        "posted_on": "Posted Today",
        "url": "https://x",
        "sponsorship": sponsorship,
        "first_seen": DAY,
        "verdict": v,
    }


def test_gap_line_names_partial_and_gap_factors_with_the_missing_skill():
    assert fit.gap_line({"factors": factors(skills="gap", domain="partial")}) == "gaps: skills (Databricks), domain"
    assert fit.gap_line({"factors": factors(level="partial")}) == "gaps: level"
    assert fit.gap_line({"factors": factors()}) is None
    assert fit.gap_line({"score_entry": 4}) is None  # stored before factors existed
    assert fit.gap_line({"factors": []}) is None  # decided by rule


def test_gap_line_keeps_the_skill_short_or_leaves_it_out():
    def skills(note):
        return fit.gap_line({"factors": [{"factor": "skills", "verdict": "partial", "note": note}]})

    assert skills("Missing: dbt, Airflow.") == "gaps: skills (dbt)"
    assert skills("missing Kubernetes") == "gaps: skills (Kubernetes)"
    assert skills("Missing: Node.js. Everything else is on the resume.") == "gaps: skills (Node.js)"
    assert skills("Missing: .NET.") == "gaps: skills (.NET)"
    assert skills("Nothing important missing.") == "gaps: skills"
    assert skills("Missing:") == "gaps: skills"
    assert skills("") == "gaps: skills"


def test_apply_and_entry_rows_carry_the_gap_line_and_maybe_does_not():
    rows = [
        job("Data Engineer", 4, factors=factors(skills="gap", domain="partial")),
        job("Junior Data Scientist", 3, factors=factors(level="gap")),
        job("Data Scientist", 4, sponsorship="unknown", factors=factors(skills="gap")),
    ]
    _, md = digest.build({"ran_at": DAY}, rows)
    lines = md.splitlines()
    apply_at = lines.index("    Why Data Engineer.")
    assert lines[apply_at + 1] == "    gaps: skills (Databricks), domain"
    assert lines[lines.index("    Why Junior Data Scientist.") + 1] == "    gaps: level"
    maybe_at = lines.index("    Why Data Scientist.")
    assert "## Maybe (1)" in md and not lines[maybe_at + 1].startswith("    gaps:")


def test_old_verdicts_still_digest_without_a_gap_line():
    rows = [job("Data Engineer", 4), job("Junior Data Scientist", 3)]
    _, md = digest.build({"ran_at": DAY}, rows)
    assert "## Apply (1)" in md and "## Entry level (1)" in md and "gaps:" not in md


def test_factors_do_not_move_a_posting_between_sections():
    plain = [job("Data Engineer", 4), job("Junior Data Scientist", 3), job("Data Scientist", 4, sponsorship="unknown")]
    rich = [job(j["title"], digest.best(j), j["sponsorship"], factors=factors(skills="gap")) for j in plain]
    names = lambda s: {k: [j["title"] for j in v] for k, v in s.items()}  # noqa: E731
    assert names(digest.sections(plain)) == names(digest.sections(rich))
