"""The favicon route and file: browsers ask for /favicon.ico at the root, the page links web/favicon.svg."""

import importlib
import io
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def test_favicon_ico_redirects_to_the_svg(monkeypatch):
    with monkeypatch.context() as patch:
        patch.setattr(sys, "stdout", io.TextIOWrapper(io.BytesIO(), encoding="utf-8"))
        server = importlib.import_module("server")
    response = server.favicon()
    assert response.status_code == 307
    assert response.headers["location"] == "/web/favicon.svg"


def test_favicon_svg_is_valid_and_linked():
    root = ET.parse("web/favicon.svg").getroot()
    assert root.tag.endswith("svg") and root.get("viewBox") == "0 0 32 32"
    assert 'rel="icon" href="favicon.svg"' in Path("web/index.html").read_text(encoding="utf-8")
