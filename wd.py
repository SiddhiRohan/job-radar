"""Workday careers JSON client: search, description fetch, caching, polite retries."""
import hashlib
import html
import json
import re
import time
from pathlib import Path

import requests

CACHE_DIR = Path(".cache")
CACHE_TTL = 6 * 3600
SLEEP_BETWEEN = 1.5
HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/128.0 Safari/537.36",
}


def base_url(tenant, shard):
    return f"https://{tenant}.{shard}.myworkdayjobs.com"


def _cache_path(url, body):
    key = hashlib.sha256((url + json.dumps(body, sort_keys=True)).encode()).hexdigest()
    return CACHE_DIR / f"{key}.json"


def request_json(url, body=None, retries=4):
    """GET (body None) or POST json. Cached for CACHE_TTL. Retries on 429/5xx."""
    path = _cache_path(url, body)
    if path.exists() and time.time() - path.stat().st_mtime < CACHE_TTL:
        return json.loads(path.read_text(encoding="utf-8"))

    delay = 3.0
    for attempt in range(retries):
        time.sleep(SLEEP_BETWEEN)
        if body is None:
            r = requests.get(url, headers=HEADERS, timeout=30)
        else:
            r = requests.post(url, headers=HEADERS, json=body, timeout=30)
        if r.status_code == 429 or r.status_code >= 500:
            if attempt == retries - 1:
                r.raise_for_status()
            time.sleep(delay)
            delay *= 2
            continue
        r.raise_for_status()
        data = r.json()
        CACHE_DIR.mkdir(exist_ok=True)
        path.write_text(json.dumps(data), encoding="utf-8")
        return data


def parse_days_ago(posted_on):
    """'Posted Today' -> 0, 'Posted Yesterday' -> 1, 'Posted 3 Days Ago' -> 3, '30+' -> 30."""
    s = (posted_on or "").lower()
    if "today" in s:
        return 0
    if "yesterday" in s:
        return 1
    m = re.search(r"(\d+)\+?\s*day", s)
    if m:
        return int(m.group(1))
    return 999


def normalize(company, tenant, shard, site, p):
    bullets = p.get("bulletFields") or []
    ext = p.get("externalPath", "")
    m = re.search(r"_([A-Za-z]*\d[\w-]*)$", ext)
    req_id = bullets[0] if bullets else (m.group(1) if m else ext)
    return {
        "company": company,
        "title": p.get("title", ""),
        "location": p.get("locationsText", ""),
        "posted_on": p.get("postedOn", ""),
        "posted_days_ago": parse_days_ago(p.get("postedOn")),
        "req_id": req_id,
        "url": f"{base_url(tenant, shard)}/en-US/{site}{ext}",
        "detail_path": f"/wday/cxs/{tenant}/{site}{ext}",
    }


def search(tenant, shard, site, text, max_pages=10, company=None, limit=20):
    """Page through Workday search results; return list of normalized postings."""
    company = company or tenant
    url = f"{base_url(tenant, shard)}/wday/cxs/{tenant}/{site}/jobs"
    out = []
    for page in range(max_pages):
        body = {"appliedFacets": {}, "limit": limit, "offset": page * limit, "searchText": text}
        data = request_json(url, body)
        if "jobPostings" not in data:
            raise ValueError(f"unexpected Workday response keys: {list(data)[:10]}")
        postings = data["jobPostings"]
        out.extend(normalize(company, tenant, shard, site, p) for p in postings)
        if len(postings) < limit or len(out) >= data.get("total", 0):
            break
    return out


def count(tenant, shard, site):
    """Return total open roles on a site (empty search). Raises on bad response."""
    url = f"{base_url(tenant, shard)}/wday/cxs/{tenant}/{site}/jobs"
    data = request_json(url, {"appliedFacets": {}, "limit": 1, "offset": 0, "searchText": ""})
    if "total" not in data or "jobPostings" not in data:
        raise ValueError(f"unexpected Workday response keys: {list(data)[:10]}")
    return data["total"]


def html_to_text(s):
    s = re.sub(r"<(br|/p|/li|/div|/h\d|/tr)\s*/?>", "\n", s, flags=re.I)
    s = re.sub(r"<li[^>]*>", "- ", s, flags=re.I)
    s = re.sub(r"<[^>]+>", "", s)
    s = html.unescape(s)
    s = re.sub(r"[ \t\xa0]+", " ", s)
    return re.sub(r"\n\s*\n+", "\n\n", s).strip()


def fetch_description(tenant, shard, detail_path):
    """Plain-text job description (and country if Workday provides it)."""
    data = request_json(base_url(tenant, shard) + detail_path)
    info = data.get("jobPostingInfo")
    if not info or "jobDescription" not in info:
        raise ValueError(f"unexpected detail response keys: {list(data)[:10]}")
    return html_to_text(info["jobDescription"])


if __name__ == "__main__":
    import sys
    jobs = search("nvidia", "wd5", "NVIDIAExternalCareerSite", " ".join(sys.argv[1:]) or "data scientist",
                  max_pages=1, company="NVIDIA")
    for j in jobs[:5]:
        print(j["posted_days_ago"], j["req_id"], j["title"], "|", j["location"])
    print(fetch_description("nvidia", "wd5", jobs[0]["detail_path"])[:400])
