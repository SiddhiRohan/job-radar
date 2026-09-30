"""Only the app's own page may change things: writes from other websites are refused, terminals and reads pass."""

import server


def test_writes_from_other_websites_are_refused():
    assert not server.allowed("POST", "https://evil.example")
    assert not server.allowed("POST", "null")  # sandboxed frames and local files
    assert not server.allowed("DELETE", "http://localhost.evil.example")


def test_the_app_itself_terminals_and_reads_pass():
    assert server.allowed("POST", "http://localhost:8000") and server.allowed("POST", "http://127.0.0.1:8766")
    assert server.allowed("POST", None)  # curl and scripts send no origin
    assert server.allowed("GET", "https://evil.example")  # reads change nothing
