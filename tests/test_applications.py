"""applications.md read, write and status changes."""

from radar import applications


def test_round_trip_and_forward_only(tmp_path):
    p = tmp_path / "applications.md"
    row = {
        "date": "2026-09-20 10:00",
        "company": "GM",
        "title": "Data | Engineer",
        "status": "screen",
        "folder": "",
        "req_id": "R1",
    }
    applications.write([row], p)
    rows = applications.rows(p)
    assert rows[0]["title"] == "Data / Engineer" and rows[0]["status"] == "screen"
    assert applications.set_status("GM", "R1", "applied", forward_only=True, path=p) is None
    assert applications.set_status("GM", "R1", "interview", forward_only=True, path=p) == ("screen", "interview")
    assert applications.set_status("GM", "R1", "hired", path=p) is None
    assert applications.set_status("GM", "R9", "offer", path=p) is None
    assert applications.set_status("GM", "R1", "applied", path=p) == (
        "interview",
        "applied",
    )  # a person may move it back


def test_undo_only_while_still_applied(tmp_path):
    p = tmp_path / "applications.md"
    base = {"date": "2026-09-20 10:00", "company": "GM", "title": "Data Engineer", "folder": ""}
    applications.write([dict(base, status="applied", req_id="R1"), dict(base, status="rejected", req_id="R2")], p)
    assert applications.remove("GM", "R1", p)["req_id"] == "R1"
    assert applications.remove("GM", "R2", p) is None  # an email moved it on; the undo must not erase that
    assert applications.remove("GM", "R9", p) is None
    assert [r["req_id"] for r in applications.rows(p)] == ["R2"]
