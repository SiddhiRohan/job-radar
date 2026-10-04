"""python run.py [--days N]: poll, score, digest, prepare, mail, watch, agents, brief. Only a poll failure stops
the run."""

import argparse
import subprocess
import sys

from radar import runlock


def step(name, args):
    print(f"\n===== {name} =====", flush=True)
    r = subprocess.run([sys.executable, "-m", name] + args)
    if r.returncode:
        print(f"!! {name} exited with {r.returncode}", flush=True)
    return r.returncode


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, help="widen the posted-within window (default from config.json)")
    ap.add_argument("--all-tiers", action="store_true", help="poll tier 3 companies too")
    args = ap.parse_args()
    poll_args = (["--days", str(args.days)] if args.days is not None else []) + (
        ["--all-tiers"] if args.all_tiers else []
    )
    # One run at a time: the web app's schedule, the OS scheduler and a manual run may all start at once.
    if not runlock.acquire():
        print(f"another run has been going since {runlock.since()}; not starting a second one", flush=True)
        return
    try:
        steps(poll_args)
    finally:
        runlock.release()


def steps(poll_args):
    if step("radar.poll", poll_args):
        sys.exit("poll failed; not scoring or digesting")
    step("radar.score", [])
    step("radar.digest", [])
    step("radar.prepare", [])  # plans the Apply rows so Tailor opens instantly; failures do not block
    step("radar.mail", [])  # reads hiring emails and moves application statuses; off until Gmail is set up
    step("radar.watch", [])  # re-reads the posting behind every open application: closed, retitled, repriced
    step("radar.agents", ["run"])  # prep, follow-ups and waiting debriefs; without a key they wait for an assistant
    step("radar.brief", [])  # what to apply to first, what changed, what went quiet


if __name__ == "__main__":
    main()
