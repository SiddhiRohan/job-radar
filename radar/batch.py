"""Score postings through the Message Batches API: half the price of asking about one posting at a time, with the
answers arriving within the hour instead of within seconds. On with "score_batch": true in config.json.

A request the batch does not answer (it errored or expired, or the whole batch outlasted the wait) is left out of the
result, and score.py asks about that posting directly, so a run still ends with every posting under the cap scored."""

import json
import time

import requests

URL = "https://api.anthropic.com/v1/messages/batches"
WAIT_SECONDS = 60 * 60  # most batches end within the hour
CANCEL_SECONDS = 5 * 60  # after a cancel, how long to wait for it to settle before reading what did finish
POLL_SECONDS = 30


def headers(api_key):
    return {"x-api-key": api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"}


def submit(api_key, bodies):
    """Send Messages API bodies as one batch, each named by its position. Returns the batch id."""
    reqs = [{"custom_id": f"p{i}", "params": b} for i, b in enumerate(bodies)]
    r = requests.post(URL, headers=headers(api_key), json={"requests": reqs}, timeout=120)
    if r.status_code != 200:
        raise RuntimeError(f"batch API {r.status_code}: {r.text[:300]}")
    return r.json()["id"]


def status(api_key, batch_id):
    """The batch record, or None when the check fails; a failed check is simply made again on the next poll."""
    try:
        r = requests.get(f"{URL}/{batch_id}", headers=headers(api_key), timeout=60)
    except requests.RequestException:
        return None
    return r.json() if r.status_code == 200 else None


def wait(api_key, batch_id, seconds, sleep=time.sleep, clock=time.monotonic):
    """Poll until the batch has ended and return its record, or None when it has not ended within the seconds given."""
    start = clock()
    while True:
        b = status(api_key, batch_id)
        if b and b.get("processing_status") == "ended":
            return b
        if clock() - start >= seconds:
            return None
        sleep(POLL_SECONDS)


def answers(api_key, batch):
    """{position: (verdict, model)} for each request that succeeded with a readable verdict; the rest are left out."""
    r = requests.get(batch["results_url"], headers=headers(api_key), timeout=120)
    r.raise_for_status()
    out = {}
    for line in filter(str.strip, r.text.splitlines()):
        row = json.loads(line)
        result = row.get("result") or {}
        if result.get("type") != "succeeded":
            continue
        msg = result["message"]
        if msg.get("stop_reason") == "refusal":
            verdict = {"error": "refusal"}
        else:
            try:
                verdict = json.loads("".join(b["text"] for b in msg["content"] if b["type"] == "text"))
            except json.JSONDecodeError:  # cut off at max_tokens: asked again directly
                continue
        out[int(row["custom_id"][1:])] = (verdict, msg.get("model"))
    return out


def score(api_key, bodies, sleep=time.sleep, clock=time.monotonic):
    """Run the bodies as one batch; {position: (verdict, model)} for the ones it answered, {} when it could not run."""
    try:
        batch_id = submit(api_key, bodies)
    except (requests.RequestException, RuntimeError, KeyError, ValueError) as e:
        print(f"  batch not sent ({str(e)[:200]}); asking directly", flush=True)
        return {}
    print(f"  batch {batch_id} sent, {len(bodies)} to score; waiting up to {WAIT_SECONDS // 60} minutes", flush=True)
    done = wait(api_key, batch_id, WAIT_SECONDS, sleep, clock)
    if done is None:
        print("  the batch outlasted the wait; cancelling it and asking about the rest directly", flush=True)
        try:
            requests.post(f"{URL}/{batch_id}/cancel", headers=headers(api_key), timeout=60)
        except requests.RequestException:
            pass
        done = wait(api_key, batch_id, CANCEL_SECONDS, sleep, clock)
        if done is None:
            return {}
    try:
        got = answers(api_key, done)
    except (requests.RequestException, KeyError, ValueError) as e:
        print(f"  batch results unreadable ({str(e)[:200]}); asking directly", flush=True)
        return {}
    print(f"  the batch answered {len(got)} of {len(bodies)}", flush=True)
    return got
