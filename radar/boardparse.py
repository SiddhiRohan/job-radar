"""Greenhouse, Lever and Ashby board JSON as postings in the shape poll.py builds for Workday. Each posting carries the
detail record the board already includes under "detail" (description, places, country), so enrichment needs no
second request. Field names were checked against one live response per system on 2026-09-27."""

import html
import re
from datetime import datetime, timezone

from radar import filters, salary, wd

US_NAMES = {"us", "usa", "u.s.", "u.s.a.", "united states", "united states of america"}


def when(value):
    """Aware datetime from an ISO 8601 string or epoch milliseconds; None when missing or unreadable."""
    try:
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(value / 1000, timezone.utc)
        dt = datetime.fromisoformat(value)
    except (TypeError, ValueError, OverflowError, OSError):
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def days_ago(dt, now=None):
    """Calendar days (UTC) since the posting date; 999, outside every window, when the board gives no date."""
    if dt is None:
        return 999
    today = (now or datetime.now(timezone.utc)).astimezone(timezone.utc).date()
    return max(0, (today - dt.astimezone(timezone.utc).date()).days)


def posted_on(days):
    """Workday's wording for the same age, so pages and digests read alike whatever the source."""
    if days >= 999:
        return ""
    if days <= 1:
        return ("Posted Today", "Posted Yesterday")[days]
    return "Posted 30+ Days Ago" if days >= 30 else f"Posted {days} Days Ago"


def split_places(text):
    """'New York, NY; London, UK' -> ['New York, NY', 'London, UK']: boards join several places with ; or |."""
    return [p.strip() for p in re.split(r"[;|]", text or "") if p.strip()]


def is_us(country):
    return (country or "").strip().lower() in US_NAMES


def non_us(places):
    """True when every (place, country) pair lies outside the US. A country from the board decides for its place; a
    place without one is read by its words, like Workday's listing check. One US or unclear place keeps the posting."""
    return bool(places) and all(not is_us(c) if c else filters.looks_non_us(p) for p, c in places)


def with_pay(text, pay):
    """Put the board's own pay figure first when the description states no range, so salary.py can read it."""
    return f"Pay range: {pay}\n\n{text}" if pay and not salary.ranges(text) else text


def jobs_in(data, ats):
    """The postings in a board response (Lever sends a bare list); anything else raises so the poll records it."""
    jobs = data if ats == "lever" else (data.get("jobs") if isinstance(data, dict) else None)
    if not isinstance(jobs, list):
        raise ValueError(f"unexpected {ats} response: {str(data)[:100]}")
    return [p for p in jobs if isinstance(p, dict) and p.get("id")]


def posting(company, ats, now, p_id, title, dt, url, places, text, **extra):
    """One posting in poll.py's shape. "detail" is what a Workday detail request returns, plus non_us; poll pops it
    and hands it to enrich. extra: country, country_code and time_type, when the board has them."""
    days, title, names = days_ago(dt, now), (title or "").strip(), [p for p, _ in places if p]
    detail = {"description": text, "title": title, "location": "; ".join(names), "additional_locations": names[1:]}
    detail.update({"country": None, "country_code": None, "time_type": None, **extra}, non_us=non_us(places))
    return {
        "company": company,
        "title": title,
        "location": detail["location"],
        "posted_on": posted_on(days),
        "posted_days_ago": days,
        "req_id": str(p_id),
        "url": url or "",
        "ats": ats,
        "detail": detail,
    }


def greenhouse(company, data, now=None):
    """boards-api.greenhouse.io/v1/boards/{board}/jobs?content=true. content is HTML escaped once more, and
    first_published is the posting date (updated_at moves whenever the employer edits the board)."""
    out = []
    for p in jobs_in(data, "greenhouse"):
        places = [(x, None) for x in split_places((p.get("location") or {}).get("name"))]
        text = wd.html_to_text(html.unescape(p.get("content") or ""))
        dt, url = when(p.get("first_published")) or when(p.get("updated_at")), p.get("absolute_url")
        out.append(posting(company, "greenhouse", now, p["id"], p.get("title"), dt, url, places, text))
    return out


def lever_pay(r):
    """'$120,000 - $150,000 per year' from Lever's salaryRange, US dollars only; None when absent or unreadable."""
    try:
        per = "hour" if "hour" in (r.get("interval") or "") else "year"
        fmt = "${:,.2f}" if per == "hour" else "${:,.0f}"
        if (r.get("currency") or "USD").upper() == "USD":
            return f"{fmt.format(float(r['min']))} - {fmt.format(float(r.get('max') or r['min']))} per {per}"
    except (AttributeError, KeyError, TypeError, ValueError):
        pass
    return None


def lever(company, data, now=None):
    """api.lever.co/v0/postings/{board}?mode=json. The page is descriptionPlain, then lists[] (a heading and HTML
    bullets each), then additionalPlain; country is the ISO code of the first place."""
    out = []
    for p in jobs_in(data, "lever"):
        cat = p.get("categories") or {}
        first, code = (cat.get("location") or "").strip(), (p.get("country") or "").strip().upper() or None
        others = [x.strip() for x in cat.get("allLocations") or [] if x and x.strip() != first]
        lists = [f"{s.get('text') or ''}\n{wd.html_to_text(s.get('content') or '')}" for s in p.get("lists") or []]
        parts = [p.get("descriptionPlain"), *lists, p.get("additionalPlain")]
        text = with_pay("\n\n".join(x.strip() for x in parts if x and x.strip()), lever_pay(p.get("salaryRange")))
        places, dt, url = [(first, code)] + [(x, None) for x in others], when(p.get("createdAt")), p.get("hostedUrl")
        extra = {"country": code, "country_code": code, "time_type": cat.get("commitment")}
        out.append(posting(company, "lever", now, p["id"], p.get("text"), dt, url, places, text, **extra))
    return out


def ashby_country(p):
    return (((p.get("address") or {}).get("postalAddress") or {}).get("addressCountry") or "").strip() or None


def ashby(company, data, now=None):
    """api.ashbyhq.com/posting-api/job-board/{board}?includeCompensation=true. Every place carries its country;
    pay lives only in compensation, not in the description. Unlisted postings are skipped."""
    out = []
    for p in jobs_in(data, "ashby"):
        if p.get("isListed") is False:
            continue
        places = [(p.get("location") or "", ashby_country(p))]
        places += [(s.get("location") or "", ashby_country(s)) for s in p.get("secondaryLocations") or []]
        comp = p.get("compensation") or {}
        pay = comp.get("scrapeableCompensationSalarySummary") or comp.get("compensationTierSummary")
        text = with_pay(p.get("descriptionPlain") or wd.html_to_text(p.get("descriptionHtml") or ""), pay)
        country, dt, url = places[0][1], when(p.get("publishedAt")), p.get("jobUrl")
        code = "US" if is_us(country) else None  # any other country already counts through places in non_us
        extra = {"country": country, "country_code": code, "time_type": p.get("employmentType")}
        out.append(posting(company, "ashby", now, p["id"], p.get("title"), dt, url, places, text, **extra))
    return out
