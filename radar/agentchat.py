"""The agents as tools for the chat assistant: interview prep and debriefs, follow-up drafts, skill gaps, the sponsor
map and the filter audit."""

from radar import agents, agentview, debrief, gaps, sponsormap

COMPANY = {"type": "string", "description": "The employer, as on the application"}
TOOLS = [
    {
        "name": "interview_debrief",
        "description": "After a screen or an interview: keep their account of how it went and write the debrief: each "
        "question with a stronger answer where theirs was weak, what the interviewer seemed unsure about and how to "
        "address it, what they promised to send, what to prepare next, and a thank-you note to send. Pass their "
        "account in their own words, complete. Without an account it returns the debriefs already written for that "
        "employer. Writing needs an API key and takes about a minute.",
        "input_schema": {
            "type": "object",
            "properties": {
                "company": COMPANY,
                "req_id": {"type": "string"},
                "account": {"type": "string", "description": "What was asked, how they answered, names, concerns"},
            },
            "required": ["company"],
        },
    },
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
    {
        "name": "filter_audit",
        "description": "The weekly filter audit: which postings the title, seniority, domain and location rules dropped "
        "that they would probably have wanted, and the config.json changes that would have kept them. Returns the "
        "latest audit; run=true writes a new one now (needs an API key). Use for 'am I missing jobs' or 'are my "
        "filters too strict'. A change is only made when they apply it on the Agents view or say so.",
        "input_schema": {"type": "object", "properties": {"run": {"type": "boolean"}}},
    },
]
NAMES = {t["name"] for t in TOOLS}


def page(name, company=None, req_id=None, again=False):
    """What one writer made, for everyone or for one employer. For an employer it picks the one application its
    agent would (radar/agents.py todo) and writes for it first when nothing is written yet, or when asked again."""
    if not company:
        return agentview.text(name)
    items = agents.todo(name, agents.config(), (company, req_id))
    if not items:
        known = agents.matching(agents.WRITERS[name].due({}, every=True), company, req_id)
        if known and name == "followups":
            return f"every application at {known[0]['company']} has had a reply, so there is nothing to follow up"
        return f"no application at {company} on the Applied list"
    one = (items[0]["company"], items[0]["req_id"])
    text = agentview.text(name, *one)
    if not again and not text.startswith("nothing written yet"):
        return text
    r = agents.run([name], one)[name]
    if r["errors"]:
        return "could not write it: " + r["errors"][0]
    if not r["made"]:
        return (
            "no API key, so nothing was written: add one on the Setup page, or run /radar-agents in a coding assistant"
        )
    return agentview.text(name, *one)


def debrief_page(company, req_id=None, account=""):
    """Keep an account of the employer's likeliest application and debrief it, or, with no account, show what the
    debriefs of that application already say."""
    app = agents.prep.choose(agents.matching(agents.prep.due({}, every=True), company, req_id))
    if app is None:
        return f"no application at {company} on the Applied list"
    one = (app["company"], app["req_id"])
    if not account.strip():
        return agentview.text("debrief", *one)
    debrief.add(*one, account)
    r = agents.run(["debrief"], one)["debrief"]
    if r["errors"]:
        return "kept your account, but the debrief could not be written: " + r["errors"][0]
    if not r["made"]:
        return "kept your account; with no API key the debrief waits: add one on Setup, or run /radar-debrief"
    return agentview.text("debrief", *one).split("\n\n----\n\n")[0]  # the round just written


def call(name, args):
    if name == "interview_debrief":
        return {"text": debrief_page(args.get("company", ""), args.get("req_id"), args.get("account", ""))[:8000]}
    if name == "interview_prep":
        return {"text": page("prep", args.get("company", ""), args.get("req_id"), bool(args.get("again")))[:8000]}
    if name == "follow_ups":
        return {"text": page("followups", args.get("company"), args.get("req_id"))[:8000]}
    if name == "skill_gaps":
        return {"lines": gaps.summary(gaps.analyse(), limit=8)}
    if name == "filter_audit":
        return {"text": audit_page(bool(args.get("run")))[:8000]}
    return {"lines": sponsormap.summary(sponsormap.analyse())}


def audit_page(run=False):
    """The latest filter audit, written first when asked or when there is none yet."""
    if run or not agents.audit.load().get("made"):
        r = agents.run(["audit"], ("", None))["audit"]  # no employer: the audit is one item, asked for now
        if r["errors"]:
            return "the audit could not be written: " + r["errors"][0]
        if not r["made"]:
            return "no API key, so no audit was written: add one on Setup, or run /radar-audit in a coding assistant"
    return agentview.text("audit")
