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


JOB_URL = re.compile(
    r"https://([\w-]+)\.(wd\d+)\.myworkdayjobs\.com/(?:[a-z]{2}-[A-Z]{2}/)?([^/]+)(/job/.+?)(?:/apply.*)?/?$"
)


def parse_job_url(url):
    """(tenant, shard, site, external_path, req_id) from a Workday job URL, or None if it is not one."""
    m = JOB_URL.match(url.strip())
    if not m:
        return None
    tenant, shard, site, ext = m.groups()
    req = re.search(r"_([A-Za-z]*[\w-]*\d[\w-]*)$", ext)
    req_id = re.sub(r"-\d+$", "", req.group(1)) if req else ext.rsplit("/", 1)[-1]  # drop Workday's -1 revision suffix
    return tenant, shard, site, ext, req_id


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
    out, total = [], None
    for page in range(max_pages):
        body = {"appliedFacets": {}, "limit": limit, "offset": page * limit, "searchText": text}
        data = request_json(url, body)
        if "jobPostings" not in data:
            raise ValueError(f"unexpected Workday response keys: {list(data)[:10]}")
        if total is None:  # Workday only reports total on the first page (0 afterwards)
            total = data.get("total", 0)
        postings = data["jobPostings"]
        out.extend(normalize(company, tenant, shard, site, p) for p in postings)
        if len(postings) < limit or len(out) >= total:
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


def fetch_detail(tenant, shard, detail_path):
    """Detail record: plain-text description plus the real location fields Workday exposes."""
    data = request_json(base_url(tenant, shard) + detail_path)
    info = data.get("jobPostingInfo")
    if not info or "jobDescription" not in info:
        raise ValueError(f"unexpected detail response keys: {list(data)[:10]}")
    req_loc = info.get("jobRequisitionLocation") or {}
    return {
        "description": html_to_text(info["jobDescription"]),
        "location": info.get("location"),
        "additional_locations": info.get("additionalLocations") or [],
        "country": (info.get("country") or {}).get("descriptor"),
        "country_code": (req_loc.get("country") or {}).get("alpha2Code"),
        "time_type": info.get("timeType"),
    }


def fetch_description(tenant, shard, detail_path):
    return fetch_detail(tenant, shard, detail_path)["description"]
