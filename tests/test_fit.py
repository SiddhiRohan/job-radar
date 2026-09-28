"""The verdict schema sent as structured output, and reading the model's factors back from stored verdicts."""

import json

from radar import fit

# The schema keywords the structured-output endpoint accepts that this schema needs. minimum and maximum were sent
# once and the API answered 400, so anything outside this list fails here first.
ALLOWED = {"type", "enum", "properties", "required", "additionalProperties", "items"}
TYPES = {"object": dict, "array": list, "string": str, "integer": int, "boolean": bool, "null": type(None)}
# The fields the digest, the sections and the UI read, exactly as they were before factors were added.
BEFORE_FACTORS = {
    "score_entry": {"type": "integer", "enum": [1, 2, 3, 4, 5]},
    "score_experienced": {"type": "integer", "enum": [1, 2, 3, 4, 5]},
    "recommended_resume": {"type": "string", "enum": ["entry", "experienced"]},
    "recommended_variant": {"type": "string"},
    "years_required": {"type": ["integer", "null"]},
    "hard_requirements_missing": {"type": "array", "items": {"type": "string"}},
    "platform_tools_missing": {"type": "array", "items": {"type": "string"}},
    "sponsorship": {"type": "string", "enum": ["yes", "likely", "unknown", "unlikely", "no", "perm_ad"]},
    "sponsorship_evidence": {"type": ["string", "null"]},
    "cover_letter_required": {"type": "boolean"},
    "why": {"type": "string"},
    "apply": {"type": "boolean"},
}


def factor(name, verdict="meets", note=""):
    return {"factor": name, "verdict": verdict, "posting": f"{name} ask", "resume": f"{name} proof", "note": note}


VERDICT = {
    "factors": [factor(n) for n in fit.MODEL_FACTORS],
    "score_entry": 4,
    "score_experienced": 3,
    "recommended_resume": "entry",
    "recommended_variant": "DS and DE Resumes/one-page",
    "years_required": None,
    "hard_requirements_missing": [],
    "platform_tools_missing": [],
    "sponsorship": "unknown",
    "sponsorship_evidence": None,
    "cover_letter_required": False,
    "why": "Pipelines match.",
    "apply": True,
}


def walk(node, path="schema"):
    yield path, node
    for name, sub in node.get("properties", {}).items():
        yield from walk(sub, f"{path}.{name}")
    if "items" in node:
        yield from walk(node["items"], f"{path}[]")


def valid(value, schema):
    """A small JSON Schema check for the keywords in ALLOWED; jsonschema is not a project dependency."""
    types = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
    if not any(isinstance(value, TYPES[t]) and not (t == "integer" and isinstance(value, bool)) for t in types):
        return False
    if "enum" in schema and value not in schema["enum"]:
        return False
    if isinstance(value, dict):
        return set(value) == set(schema["required"]) and all(valid(value[k], schema["properties"][k]) for k in value)
    return all(valid(x, schema["items"]) for x in value) if isinstance(value, list) else True


def test_schema_uses_only_keywords_the_endpoint_accepts():
    for path, node in walk(fit.SCHEMA):
        assert set(node) <= ALLOWED, f"{path}: {set(node) - ALLOWED}"
        if node.get("type") == "object":
            assert node["additionalProperties"] is False, path
            assert node["required"] == list(node["properties"]), path
    assert json.loads(json.dumps(fit.SCHEMA)) == fit.SCHEMA  # sent as JSON exactly as written, no tuples


def test_factors_are_required_and_limited_to_known_names_and_verdicts():
    assert "factors" in fit.SCHEMA["required"]
    item = fit.SCHEMA["properties"]["factors"]["items"]
    assert item["properties"]["factor"]["enum"] == ["experience", "level", "skills", "domain"]
    assert item["properties"]["verdict"]["enum"] == ["meets", "partial", "gap"]
    assert item["required"] == ["factor", "verdict", "posting", "resume", "note"]


def test_fields_from_before_factors_are_unchanged():
    props = {k: v for k, v in fit.SCHEMA["properties"].items() if k != "factors"}
    assert props == BEFORE_FACTORS and list(props) == list(BEFORE_FACTORS)


def test_schema_accepts_a_full_verdict_and_rejects_broken_ones():
    assert valid(VERDICT, fit.SCHEMA)
    assert not valid({k: v for k, v in VERDICT.items() if k != "factors"}, fit.SCHEMA)
    assert not valid(dict(VERDICT, factors=[factor("keywords")]), fit.SCHEMA)
    assert not valid(dict(VERDICT, factors=[dict(factor("level"), verdict="strong")]), fit.SCHEMA)
    assert not valid(dict(VERDICT, factors=[dict(factor("level"), score=3)]), fit.SCHEMA)
    try:
        import jsonschema
    except ImportError:  # installed on some machines only; the checks above always run
        return
    jsonschema.Draft202012Validator.check_schema(fit.SCHEMA)
    jsonschema.validate(VERDICT, fit.SCHEMA)


def test_prompt_asks_for_each_factor_by_experience_not_keywords():
    for word in (*fit.MODEL_FACTORS, *fit.VERDICTS, "not keyword overlap", '"Missing: '):
        assert word in fit.RULES, word


def test_old_verdicts_and_errors_have_no_factors():
    assert fit.model_factors({"score_entry": 4, "why": "stored before factors"}) == []
    assert fit.model_factors({"error": "API 500"}) == []
    assert fit.model_factors(None) == []
    assert fit.model_factors({"factors": "experience"}) == []
    assert fit.model_factors({"factors": {"factor": "level"}}) == []


def test_factors_are_read_back_in_order_one_per_name():
    raw = [
        factor("domain", "gap"),
        "not a factor",
        {"factor": "skills", "verdict": "partial", "posting": None, "note": "Missing: Databricks."},
        factor("keywords"),
        dict(factor("level"), verdict="great"),
        factor("domain", "meets"),
        factor("experience"),
    ]
    got = fit.model_factors({"factors": raw})
    assert [f["factor"] for f in got] == ["experience", "skills", "domain"]
    assert got[1] == {
        "factor": "skills",
        "verdict": "partial",
        "posting": "",
        "resume": "",
        "note": "Missing: Databricks.",
    }
    assert got[2]["verdict"] == "gap"  # the first of two domain entries wins
