"""python run.py [--days N]: poll -> score -> digest. Score failures don't block the digest."""

import argparse
import subprocess
import sys


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
    if step("radar.poll", poll_args):
        sys.exit("poll failed; not scoring or digesting")
    step("radar.score", [])
    step("radar.digest", [])
    step("radar.prepare", [])  # plans the Apply rows so Tailor opens instantly; failures do not block


if __name__ == "__main__":
    main()
