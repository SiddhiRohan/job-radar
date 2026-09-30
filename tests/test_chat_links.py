"""The chat does what the terminal does with a link: judge one posting, or add its employer. Offline: the fetch,
the scoring and the one check request are replaced."""

from radar import chat, evaluate

POSTING = {
    "company": "Contoso",
    "title": "Data Engineer",
    "location": "Austin, TX",
    "req_id": "R1000592",
    "url": "https://contoso.wd5.myworkdayjobs.com/en-US/Careers/job/Austin-TX/Data-Engineer_R1000592",
    "verdict": {"score_entry": 3, "score_experienced": 4, "recommended_resume": "experienced", "why": "Synthetic."},
}


def test_both_link_tools_are_offered():
    names = {t["name"] for t in chat.TOOLS}
    assert {"evaluate_link", "add_employer"} <= names
    assert "evaluate_link" in chat.SYSTEM and "add_employer" in chat.SYSTEM


def test_evaluate_link_returns_the_terminal_summary(monkeypatch):
    monkeypatch.setattr(evaluate, "ingest_url", lambda url: POSTING)
    out = chat.server_tool("evaluate_link", {"url": POSTING["url"]}, {})
    assert (
        out["posting"][0].startswith("Contoso | Data Engineer") and "fit: entry 3 / experienced 4" in out["posting"][1]
    )


def test_a_bad_link_comes_back_as_words_not_a_crash(monkeypatch):
    def refuse(url):
        raise ValueError("that is not a job link the radar reads")

    monkeypatch.setattr(evaluate, "ingest_url", refuse)
    assert chat.server_tool("evaluate_link", {"url": "https://example.com"}, {}) == {
        "error": "that is not a job link the radar reads"
    }


def test_add_employer_goes_through_the_add_command(monkeypatch):
    from companies import add

    calls = []
    monkeypatch.setattr(add, "add", lambda name, url: calls.append((name, url)) or {"ok": True, "message": "added"})
    out = chat.server_tool("add_employer", {"name": "Fabrikam", "url": "https://jobs.lever.co/fabrikam"}, {})
    assert out == {"ok": True, "message": "added"} and calls == [("Fabrikam", "https://jobs.lever.co/fabrikam")]
