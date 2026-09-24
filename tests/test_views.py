"""View sections must not share an id with a nav hash: the browser would jump to them and hide the header."""

import re
from pathlib import Path

HTML = Path("web/index.html").read_text(encoding="utf-8")


def test_no_element_id_matches_a_nav_hash():
    hashes = set(re.findall(r'<a href="#([\w-]+)" data-view=', HTML))
    ids = set(re.findall(r'\sid="([\w-]+)"', HTML))
    assert hashes == {"today", "tailor", "applied"}
    assert not hashes & ids


def test_every_nav_view_has_a_section():
    views = set(re.findall(r'<section [^>]*data-view="([\w-]+)"', HTML))
    assert views == {"today", "tailor", "applied"}
