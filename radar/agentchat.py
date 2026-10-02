"""The agents as tools for the chat assistant: interview prep, follow-up drafts, skill gaps and the sponsor map."""

from radar import agents, agentview, gaps, sponsormap

COMPANY = {"type": "string", "description": "The employer, as on the application"}
TOOLS = [
    {
        "name": "interview_prep",
        "description": "Interview prep for one application: what they will probe, likely questions with what to answer "
        "from, stories from the resume, gaps and how to address them, questions to ask, and how to answer the "
        "sponsorship question. Returns the one already written, or writes it (a minute; needs an API key). Use for "
        "'I have an interview at X' or 'prep me for X'; again=true rewrites it.",
        "input_schema": {
            "type": "object",
            "properties": {"company": COMPANY, "req_id": {"type": "string"}, "again": {"type": "boolean"}},
            "required": ["company"],
        },
    },
    {
        "name": "follow_ups",
        "description": "Follow-up drafts for quiet applications: a LinkedIn note, an email and a LinkedIn search to find "
        "the recruiter. Without company, every draft waiting to be sent; with company, that application's, written "
        "now if there is none. Drafts only: they send it themselves.",
        "input_schema": {"type": "object", "properties": {"company": COMPANY, "req_id": {"type": "string"}}},
    },
    {
        "name": "skill_gaps",
        "description": "The skills scored postings keep finding missing over the last 30 days, with how many of those "
        "postings scored 3, one point below Apply, and confirmed skills the resume fails to show. Use for 'what "
        "should I learn' or 'why do my scores stall at 3'.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "sponsor_map",
        "description": "Which employers' recent postings say they sponsor, decide per posting or rule it out, and "
        "employer defaults their own postings contradict. Use for 'who sponsors' or 'where should I apply on a visa'.",
        "input_schema": {"type": "object", "properties": {}},
    },
]
NAMES = {t["name"] for t in TOOLS}


def page(name, company=None, req_id=None, again=False):
    """What one writer made, for one employer or all of them. Asked for an employer it has nothing for (or again),
    it writes one first, for that employer's likeliest application: one at a screen or interview, else the oldest."""
    text = agentview.text(name, company, req_id)
    if not company or not (again or text.startswith("nothing written yet")):
        return text
    items = agents.todo(name, agents.config(), (company, req_id))
    if not items:
        return f"no application at {company} on the Applied list"
    one = (items[0]["company"], items[0]["req_id"])
    r = agents.run([name], one)[name]
    if r["errors"]:
        return "could not write it: " + r["errors"][0]
    if not r["made"]:
        return (
            "no API key, so nothing was written: add one on the Setup page, or run /radar-agents in a coding assistant"
        )
    return agentview.text(name, *one)


def call(name, args):
    if name == "interview_prep":
        return {"text": page("prep", args.get("company", ""), args.get("req_id"), bool(args.get("again")))[:8000]}
    if name == "follow_ups":
        return {"text": page("followups", args.get("company"), args.get("req_id"))[:8000]}
    if name == "skill_gaps":
        return {"lines": gaps.summary(gaps.analyse(), limit=8)}
    return {"lines": sponsormap.summary(sponsormap.analyse())}
