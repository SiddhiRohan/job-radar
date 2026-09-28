"""python -m radar.schedule install [HH:MM] | remove | status: run the radar every morning even when the app is closed.

Uses the operating system's own scheduler: Task Scheduler on Windows (a task named JobRadar), launchd on macOS, cron on
Linux. The task runs run.py from this folder with this Python and appends to logs/run.log. The run lock means it never
overlaps a run the app starts. Only the person using the radar installs it, from the setup page or this command.

Every check looks at the folder the scheduled run starts in, so a second copy of the radar on the same computer never
takes the first one's schedule for its own, and never replaces or removes it. A task whose folder is gone (the copy
was moved or deleted) can only fail, so any copy may replace or remove it."""

import html
import platform
import plistlib
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TASK = "JobRadar"
LABEL = "com.jobradar.daily"
MARK = "# job-radar daily run"
PLIST = Path.home() / "Library" / "LaunchAgents" / f"{LABEL}.plist"
# What follows the folder in an entry the radar makes, or in one made by hand as `cd /d <folder> && ...`. Anything
# else means another folder: job-radar-2, "job-radar - Copy", or a copy nested inside this one.
AFTER_PATH = r"""(?=[\\/]\.cache[\\/]run-daily\.cmd|["']|\s*&&|\s*$)"""
FOLDER_IN = [
    re.compile(r'cd\s+(?:/d\s+)?"([^"]+)"'),  # cd "<folder>": launchd, cron
    re.compile(r"cd\s+/d\s+([^\"&<>]+?)\s*&&"),  # cd /d <folder> &&: a task made by hand
    re.compile(r'([A-Za-z]:\\[^"<>]*?)\\\.cache\\run-daily\.cmd'),  # <folder>\.cache\run-daily.cmd: our task
]


def command(root=ROOT, python=sys.executable):
    return f'cd "{root}" && "{python}" run.py >> logs/run.log 2>&1'


def windows_script(root=ROOT, python=sys.executable):
    """Task Scheduler takes one short command line, so the task points at a small script in .cache."""
    script = root / ".cache" / "run-daily.cmd"
    script.parent.mkdir(parents=True, exist_ok=True)
    (root / "logs").mkdir(exist_ok=True)
    script.write_text(f'@echo off\r\ncd /d "{root}"\r\n"{python}" run.py >> logs\\run.log 2>&1\r\n', encoding="utf-8")
    return script


def here(text, root=ROOT):
    """True when a scheduler entry starts the radar in this folder rather than in another copy of it."""
    return re.search(re.escape(str(root).lower()) + AFTER_PATH, html.unescape(text).lower()) is not None


def stale(text):
    """True when every folder a scheduler entry starts the radar in is gone, so the entry can only fail."""
    found = [m.group(1).strip() for rx in FOLDER_IN for m in rx.finditer(html.unescape(text))]
    return bool(found) and not any((Path(f) / "run.py").exists() for f in found)


def entry(system, run=subprocess.run):
    """The scheduler's record of the daily run as text, '' when there is none. Cron may hold one line per copy."""
    if system == "Windows":
        r = run(["schtasks", "/Query", "/TN", TASK, "/XML"], capture_output=True, text=True, errors="replace")
        return r.stdout if r.returncode == 0 else ""
    if system == "Darwin":
        return PLIST.read_text(encoding="utf-8", errors="replace") if PLIST.exists() else ""
    return "\n".join(ln for ln in crontab(run) if MARK in ln)


def elsewhere(system=None, run=subprocess.run, root=ROOT):
    """True when the one Windows task or macOS agent the radar uses already starts another copy that still exists."""
    system = system or platform.system()
    if system not in ("Windows", "Darwin"):
        return False  # cron keeps a line per copy
    text = entry(system, run)
    return bool(text) and not here(text, root) and not stale(text)


def install(at="07:30", system=None, run=subprocess.run, root=ROOT):
    hh, mm = (int(x) for x in at.split(":"))
    system = system or platform.system()
    if elsewhere(system, run, root):
        return False
    if system == "Windows":
        script = windows_script(root)
        args = ["schtasks", "/Create", "/SC", "DAILY", "/ST", f"{hh:02d}:{mm:02d}", "/TN", TASK, "/TR", f'"{script}"']
        return run(args + ["/F"], capture_output=True, text=True).returncode == 0
    if system == "Darwin":
        (root / "logs").mkdir(exist_ok=True)
        spec = {
            "Label": LABEL,
            "ProgramArguments": ["/bin/sh", "-c", command(root)],
            "StartCalendarInterval": {"Hour": hh, "Minute": mm},
        }
        PLIST.parent.mkdir(parents=True, exist_ok=True)
        PLIST.write_bytes(plistlib.dumps(spec))
        run(["launchctl", "unload", str(PLIST)], capture_output=True)
        return run(["launchctl", "load", "-w", str(PLIST)], capture_output=True).returncode == 0
    (root / "logs").mkdir(exist_ok=True)
    lines = [ln for ln in crontab(run) if not mine_or_gone(ln, root)]
    lines.append(f"{mm} {hh} * * * {command(root)} {MARK}")
    return run(["crontab", "-"], input="\n".join(lines) + "\n", capture_output=True, text=True).returncode == 0


def crontab(run=subprocess.run):
    r = run(["crontab", "-l"], capture_output=True, text=True)
    return r.stdout.splitlines() if r.returncode == 0 else []


def mine_or_gone(line, root=ROOT):
    """A cron line of the radar's that starts this folder, or a folder that no longer exists."""
    return MARK in line and (here(line, root) or stale(line))


def remove(system=None, run=subprocess.run, root=ROOT):
    """Take this folder's daily run off the scheduler, and one left by a copy that is gone; another copy's schedule
    stays as it is."""
    system = system or platform.system()
    if system not in ("Windows", "Darwin"):
        try:
            have = crontab(run)
        except OSError:  # no cron on this machine, so nothing to remove
            return True
        keep = [ln for ln in have if not mine_or_gone(ln, root)]
        if len(keep) == len(have):
            return True
        return run(["crontab", "-"], input="\n".join(keep) + "\n", capture_output=True, text=True).returncode == 0
    text = entry(system, run)
    if not (here(text, root) or stale(text)):
        return True  # none, or another copy's: nothing of this folder's to remove
    if system == "Windows":
        return run(["schtasks", "/Delete", "/TN", TASK, "/F"], capture_output=True, text=True).returncode == 0
    run(["launchctl", "unload", "-w", str(PLIST)], capture_output=True)
    PLIST.unlink(missing_ok=True)
    return True


def status(system=None, run=subprocess.run, root=ROOT):
    """True when the operating system will start the daily run in this folder by itself."""
    system = system or platform.system()
    try:
        return here(entry(system, run), root)
    except OSError:  # no scheduler command on this machine
        return False


def main(argv):
    cmd = argv[0] if argv else "status"
    if cmd == "install":
        at = argv[1] if len(argv) > 1 else "07:30"
        if elsewhere():
            print("the daily task already starts another copy of the radar; remove it from that folder first")
        else:
            print(f"daily run scheduled at {at}" if install(at) else "could not create the scheduled task")
    elif cmd == "remove":
        print("daily run removed" if remove() else "could not remove the scheduled task")
    else:
        print("scheduled by the system" if status() else "not scheduled: runs only while the app is open")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
