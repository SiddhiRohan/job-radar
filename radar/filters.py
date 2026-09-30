"""Title, location, years-of-experience, and contract filters. All matching is case-insensitive."""

import re

# fmt: off
NON_US = [
    "canada", "mexico", "brazil", "argentina", "colombia", "chile", "peru", "united kingdom", "uk", "england",
    "london", "ireland", "dublin", "germany", "france", "paris", "spain", "italy", "netherlands", "amsterdam",
    "poland", "warsaw", "czech", "prague", "romania", "bucharest", "sweden", "stockholm", "denmark", "finland",
    "norway", "switzerland", "zurich", "austria", "vienna", "belgium", "brussels", "portugal", "lisbon", "hungary",
    "budapest", "israel", "tel aviv", "india", "bangalore", "bengaluru", "hyderabad", "pune", "chennai", "mumbai",
    "gurgaon", "gurugram", "noida", "delhi", "kolkata", "ahmedabad", "china", "shanghai", "beijing", "shenzhen",
    "taiwan", "taipei", "hsinchu", "japan", "tokyo", "korea", "seoul", "singapore", "malaysia", "kuala lumpur",
    "penang", "philippines", "manila", "vietnam", "hanoi", "ho chi minh", "thailand", "bangkok", "indonesia",
    "jakarta", "australia", "sydney", "melbourne", "new zealand", "hong kong", "dubai", "uae", "saudi", "riyadh",
    "egypt", "cairo", "south africa", "johannesburg", "nigeria", "lagos", "kenya", "nairobi", "turkey", "istanbul",
    "costa rica", "heredia", "guatemala", "puerto rico", "bermuda", "toronto", "vancouver", "montreal", "ottawa",
    "calgary", "munich", "berlin", "madrid", "barcelona", "milan", "rome", "krakow", "sao paulo", "bogota",
    "buenos aires", "mexico city", "monterrey", "guadalajara", "luxembourg", "copenhagen", "oslo", "helsinki",
    "athens", "edinburgh",
    # Seen on Greenhouse boards, which give no country to check a place against (2026-09-27)
    "serbia", "belgrade", "ukraine", "estonia", "cyprus", "slovenia", "ljubljana", "lithuania", "vilnius", "uruguay",
    "great britain", "british columbia", "alberta", "quebec", "manitoba", "nova scotia", "auckland", "frankfurt",
    "stuttgart", "cologne", "cork", "são paulo", "cdmx", "abu dhabi", "emea", "apac", "latam",
]
# fmt: on
# US places that share a name with a city above, as postings and Workday URLs write them. Only these pairs: a bare
# state code is not enough, since "Bengaluru, IN" and "Munich, DE" use country codes that are also state codes.
US_TWINS = re.compile(
    r"\b(vancouver,? (wa|washington)|dublin,? (oh|ohio|ca|california)|vienna,? (va|virginia)"
    r"|melbourne,? (fl|florida)|warsaw,? (in|indiana)|athens,? (ga|georgia|oh|ohio)|paris,? (tx|texas)"
    r"|rome,? (ga|georgia|ny|new york)|london,? (ky|kentucky|oh|ohio))\b"
)


def _word(phrase):
    return re.compile(r"(?<!\w)" + re.escape(phrase.lower()) + r"(?!\w)")


def looks_non_us(location):
    s = location.lower()
    if re.search(r"\b(us|usa|united states|u\.s\.)\b", s) or US_TWINS.search(s):
        return False
    return any(_word(w).search(s) for w in NON_US)


def path_non_us(url):
    """The /job/<City>/<slug> segment names a city or country; drop when it is clearly non-US."""
    m = re.search(r"/job/([^/]+)/[^/]+/?$", url)
    return bool(m) and looks_non_us(m.group(1).replace("-", " "))


def detail_non_us(detail):
    """Detail record says the primary location is outside the US and no other listed location looks US."""
    code = detail.get("country_code")
    if not code or code == "US":
        return False
    return all(looks_non_us(x) for x in detail.get("additional_locations") or [])


ENTRY = re.compile(
    r"\b(junior|jr|entry[- ]level|new (college )?grad\w*|early careers?|graduate|associate|launchpad|(engineer|scientist|developer) (i|1))\b",
    re.I,
)
NEVER_OVERRIDE = re.compile(r"\b(director|vice president|vp|avp|manager|principal|intern|internship|co-?op)\b", re.I)


def is_entry_title(title):
    return bool(ENTRY.search(title)) and not NEVER_OVERRIDE.search(title)


def title_matches_term(title, term=None, cfg=None):
    """The title must name a target role (config title_patterns). Entry-worded titles may also match the wider
    entry_title_patterns. Matching one loose word of the search term let in 'Machine Operator' and lab scientists."""
    cfg = cfg or {}
    pats = list(cfg.get("title_patterns") or [])
    if is_entry_title(title):
        pats += cfg.get("entry_title_patterns") or []
    if not pats:  # no patterns configured: fall back to the full search phrase
        return bool(term) and term.lower() in title.lower()
    return any(re.search(p, title, re.I) for p in pats)


def title_exclusion(title, cfg):
    """Return 'seniority', 'domain', or None. include_override beats both lists."""
    t = title.lower()
    if any(w.lower() in t for w in cfg.get("include_override", [])) and not NEVER_OVERRIDE.search(t):
        return None
    for key, reason in (("exclude_seniority", "seniority"), ("exclude_domain", "domain")):
        if any(_word(w).search(t) for w in cfg.get(key, [])):
            return reason
    return None


YEARS = re.compile(r"(\d{1,2})\s*(?:\+|-|–|to)?\s*(\d{1,2})?\s*\+?\s*(?:years|yrs)\b(?=[^.\n]{0,50}?experience)", re.I)


def years_required(text):
    """Smallest N from 'N+ years', 'N-M years', 'minimum of N years' phrases tied to experience. None if absent."""
    found = [int(m.group(1)) for m in YEARS.finditer(text)]
    return min(found) if found else None


CONTRACT_TITLE = re.compile(r"(?<!\w)(contract|contractor|temporary|temp|w-?2|c2c|1099)(?!\w)", re.I)
CONTRACT_TEXT = [
    r"(?<!\w)(?:w-?2|c2c|corp[- ]to[- ]corp|1099)(?!\w)",
    r"contract[- ]to[- ]hire",
    r"\d+[- ]?(?:month|week|year) contract",
    r"contract (?:role|position|assignment|opportunity|basis)",
    r"contractor (?:role|position)",
    r"temporary (?:position|role|assignment|employment)",
]


def is_contract(title, text):
    """(bool, evidence). Title words count directly; description needs a contract-role phrase."""
    m = CONTRACT_TITLE.search(title)
    if m:
        return True, f"title: {m.group(1)}"
    for p in CONTRACT_TEXT:
        m = re.search(p, text, re.I)
        if m:
            s = text[max(0, m.start() - 50) : m.end() + 50].replace("\n", " ")
            return True, re.sub(r"\s+", " ", s).strip()
    return False, None
