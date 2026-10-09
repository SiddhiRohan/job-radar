"""How the company scout checks a lead: at its careers link, with the request the poll would make, or, with no link,
on Greenhouse, Lever and Ashby under the employer's name. Each check counts the open roles and those whose title
names one of the person's target roles."""

import re

import requests

from companies import add, board
from radar import boards, filters, wd

BOARD_URL = {
    "greenhouse": "https://job-boards.greenhouse.io/{}",
    "lever": "https://jobs.lever.co/{}",
    "ashby": "https://jobs.ashbyhq.com/{}",
}


def readable(link):
    """A link on a system the poll reads: a Workday site or a Greenhouse, Lever or Ashby board."""
    return bool(link) and bool(board.board_from_url(link) or add.workday_from_url(link))


def matching(postings, cfg):
    return sum(1 for p in postings if filters.title_matches_term(p.get("title", ""), None, cfg))


def at_link(link, cfg):
    """(system, careers url, open roles, roles matching the titles) for a careers link. Raises when it answers no,
    or has no open roles: an empty board is no reason to follow an employer."""
    found, site = board.board_from_url(link), add.workday_from_url(link)
    if found:
        postings = boards.fetch({"name": found["board"]} | found)
        if not postings:
            raise ValueError("no open roles there")
        return found["ats"], BOARD_URL[found["ats"]].format(found["board"]), len(postings), matching(postings, cfg)
    if site:
        roles = wd.count(*site)
        if not roles:
            raise ValueError("no open roles there")
        hits = wd.search(*site, cfg["search_terms"][0], max_pages=1) if cfg.get("search_terms") else []
        return "workday", f"https://{site[0]}.{site[1]}.myworkdayjobs.com/{site[2]}", roles, matching(hits, cfg)
    raise ValueError("not a Workday, Greenhouse, Lever or Ashby link")


def on_boards(name, cfg):
    """The same, looked for on the three boards under the employer's name; None when no board answers with postings."""
    words = re.findall(r"[a-z0-9]+", name.lower().replace("&", " and "))
    for token in dict.fromkeys(["".join(words), "-".join(words)]):
        for ats in BOARD_URL:
            try:
                postings = boards.fetch({"name": name, "ats": ats, "board": token})
            except (requests.RequestException, ValueError, KeyError, TypeError):
                continue
            if postings:
                return ats, BOARD_URL[ats].format(token), len(postings), matching(postings, cfg)
    return None
