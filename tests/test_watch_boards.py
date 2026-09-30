"""The watcher on job-board employers: a board that stops listing a posting means it closed; an empty board does not."""

from radar import boards, watch

BOARD = {"name": "Contoso", "ats": "greenhouse", "board": "contoso", "sponsors_h1b": True, "tier": 2}
JOB = {"company": "Contoso", "req_id": "4001", "title": "Data Engineer", "description": "Build pipelines with Spark."}


def listed(*ids, title="Data Engineer"):
    return [{"req_id": i, "detail": {"title": title, "description": "Build pipelines with Spark."}} for i in ids]


def test_watch_reads_a_board_posting_as_open_or_closed():
    def find_on(postings):
        return lambda company, req_id: boards.find(company, req_id, fetch_board=lambda c: postings)

    assert watch.check({}, JOB, BOARD, find=find_on(listed("4001", "4002")))["status"] == "open"
    assert watch.check({}, JOB, BOARD, find=find_on(listed("4002")))["status"] == "closed"
    empty = watch.check({}, JOB, BOARD, find=find_on([]))
    assert empty["status"] == "unknown" and "no postings" in empty["note"]  # an empty board is not a closure
    retitled = watch.check({}, JOB, BOARD, find=find_on(listed("4001", title="Senior Data Engineer")))
    assert retitled["changes"] == ["title now: Senior Data Engineer"]
