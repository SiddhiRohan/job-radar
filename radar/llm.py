"""Thin Messages API helper shared by score.py, apply.py, letters.py, finalize.py."""

import json
import os
import sys
import time
from pathlib import Path

import requests

from radar import owner

API_URL = "https://api.anthropic.com/v1/messages"
# ANTHROPIC_MODEL in the environment or in .env picks the model; the others are fallbacks when it is not available.
MODELS = [owner.env("ANTHROPIC_MODEL", "claude-sonnet-4-6"), "claude-sonnet-5", "claude-opus-5"]


def load_api_key():
    """ANTHROPIC_API_KEY from the environment, else from a KEY=VALUE line in .env."""
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key and Path(".env").exists():
        for raw in Path(".env").read_text(encoding="utf-8").splitlines():
            name, _, value = raw.strip().partition("=")
            if name == "ANTHROPIC_API_KEY":
                key = value.strip().strip('"').strip("'")
    return key or sys.exit("ANTHROPIC_API_KEY is not set (put it in .env as ANTHROPIC_API_KEY=sk-ant-...)")


def converse(system, messages, tools, max_tokens=2048):
    """One Messages API turn with tools; returns the raw response dict (content blocks, stop_reason)."""
    headers = {"x-api-key": load_api_key(), "anthropic-version": "2023-06-01", "content-type": "application/json"}
    body = {"model": MODELS[0], "max_tokens": max_tokens, "system": system, "messages": messages, "tools": tools}
    for attempt in range(3):
        r = requests.post(API_URL, headers=headers, json=body, timeout=180)
        if r.status_code in (429, 529) or r.status_code >= 500:
            time.sleep(5 * (attempt + 1))
            continue
        break
    if r.status_code != 200:
        raise RuntimeError(f"API {r.status_code}: {r.text[:300]}")
    return r.json()


def complete(system, user, schema=None, max_tokens=4096):
    """Return (parsed JSON if schema else text, model). Retries 429/5xx; falls back through MODELS on 404."""
    headers = {"x-api-key": load_api_key(), "anthropic-version": "2023-06-01", "content-type": "application/json"}
    for model in MODELS:
        body = {
            "model": model,
            "max_tokens": max_tokens,
            "system": system,
            "messages": [{"role": "user", "content": user}],
        }
        if schema:
            body["output_config"] = {"format": {"type": "json_schema", "schema": schema}}
        for attempt in range(3):
            r = requests.post(API_URL, headers=headers, json=body, timeout=180)
            if r.status_code in (429, 529) or r.status_code >= 500:
                time.sleep(5 * (attempt + 1))
                continue
            break
        if r.status_code == 404 and "not_found" in r.text:
            print(f"  model {model} not available, trying next", flush=True)
            continue
        if r.status_code != 200:
            raise RuntimeError(f"API {r.status_code}: {r.text[:300]}")
        data = r.json()
        if data.get("stop_reason") == "refusal":
            raise RuntimeError("API refusal")
        text = "".join(b["text"] for b in data["content"] if b["type"] == "text")
        return (json.loads(text) if schema else text), model
    sys.exit(f"none of {MODELS} worked for this API key")
