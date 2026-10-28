"""The automatic offline retry in web/app.js. The suite has no JavaScript runtime, so this reads the source.

fail() shows an error and, when the server is not answering, retries once five seconds later. It used to retry
whenever any element with the error class sat in the view, so a stale timer reloaded a view the person had already
recovered with Retry and threw away what they had typed since. It must retry only while its own message shows.
"""

import re
from pathlib import Path


def fail_source():
    src = Path("web/app.js").read_text(encoding="utf-8")
    start = src.index("const fail = ")
    return src[start : src.index("\n};", start)]


def test_offline_retry_checks_its_own_message():
    body = fail_source()
    assert 'querySelector(".error")' not in body
    shown = re.search(r"if \((\w+)\.isConnected\) retry\(\)", body)
    assert shown, "the timer must check that its own message is still on the page"
    assert f"where.replaceChildren({shown.group(1)})" in body, "the node checked must be the node shown"
