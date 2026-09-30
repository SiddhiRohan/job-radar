"""The privacy guard: terms come from private files only, matches are whole words, output never shows a term."""

import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "privacy_guard", Path(__file__).parents[1] / "scripts" / "privacy_guard.py"
)
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)


def setup_private_files(tmp_path):
    (tmp_path / ".privacy-terms").write_text("# comment\nJane Quinn\nAcme Labs\n", encoding="utf-8")
    (tmp_path / ".env").write_text(
        'OWNER_SHORT="Jane"\nRESUME_FILENAME=Resume - Jane Quinn.docx\nOTHER=x\n', encoding="utf-8"
    )
    (tmp_path / "applications.md").write_text(
        "| date | company | title | status | folder | req_id |\n|---|---|---|---|---|---|\n"
        "| 2026-09-20 10:00 | Contoso | Data Engineer | applied |  | R-12345 |\n",
        encoding="utf-8",
    )


def test_terms_come_from_the_three_private_files(tmp_path):
    setup_private_files(tmp_path)
    t = guard.terms(tmp_path)
    assert {"Jane Quinn", "Acme Labs", "Jane", "Resume - Jane Quinn", "R-12345"} <= set(t)
    assert "x" not in t and t == sorted(t, key=len, reverse=True)


def test_whole_words_only_and_case_insensitive(tmp_path):
    setup_private_files(tmp_path)
    compiled = [(i + 1, guard.pattern(x)) for i, x in enumerate(guard.terms(tmp_path))]
    hits = guard.scan_text("fine line\nJanet is someone else\njane quinn wrote this\nreq R-123456 differs", compiled)
    assert [n for n, _ in hits] == [3]


def test_no_private_files_means_nothing_to_block(tmp_path):
    assert guard.terms(tmp_path) == []
