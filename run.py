"""python run.py [--days N]: poll -> score -> digest. Score failures don't block the digest."""
import argparse
import subprocess
import sys


def step(name, args):
    print(f"\n===== {name} =====", flush=True)
    r = subprocess.run([sys.executable, name] + args)
    if r.returncode:
        print(f"!! {name} exited with {r.returncode}", flush=True)
    return r.returncode


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, help="widen the posted-within window (default from config.json)")
    args = ap.parse_args()
    poll_args = ["--days", str(args.days)] if args.days is not None else []
    if step("poll.py", poll_args):
        sys.exit("poll failed; not scoring or digesting")
    step("score.py", [])
    step("digest.py", [])


if __name__ == "__main__":
    main()
