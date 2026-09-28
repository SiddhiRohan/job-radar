"""python -m radar.schedule install [HH:MM] | remove | status: run the radar every morning even when the app is closed.

Uses the operating system's own scheduler: Task Scheduler on Windows (a task named JobRadar), launchd on macOS, cron on
Linux. The task runs run.py from this folder with this Python and appends to logs/run.log. The run lock means it never
overlaps a run the app starts. Only the person using the radar installs it, from the setup page or this command."""

import platform
import plistlib
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TASK = "JobRadar"
LABEL = "com.jobradar.daily"
MARK = "# job-radar daily run"
PLIST = Path.home() / "Library" / "LaunchAgents" / f"{LABEL}.plist"


def command(root=ROOT, python=sys.executable):
    return f'cd "{root}" && "{python}" run.py >> logs/run.log 2>&1'


def windows_script(root=ROOT, python=sys.executable):
    """Task Scheduler takes one short command line, so the task points at a small script in .cache."""
    script = root / ".cache" / "run-daily.cmd"
    script.parent.mkdir(parents=True, exist_ok=True)
    (root / "logs").mkdir(exist_ok=True)
    script.write_text(f'@echo off\r\ncd /d "{root}"\r\n"{python}" run.py >> logs\\run.log 2>&1\r\n', encoding="utf-8")
    return script


def install(at="07:30", system=None, run=subprocess.run, root=ROOT):
    hh, mm = (int(x) for x in at.split(":"))
    system = system or platform.system()
    if system == "Windows":
        script = windows_script(root)
        args = [
            "schtasks",
            "/Create",
            "/SC",
            "DAILY",
            "/ST",
            f"{hh:02d}:{mm:02d}",
            "/TN",
            TASK,
            "/TR",
            f'"{script}"',
            "/F",
        ]
        return run(args, capture_output=True, text=True).returncode == 0
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
    lines = [ln for ln in crontab(run) if MARK not in ln]
    lines.append(f"{mm} {hh} * * * {command(root)} {MARK}")
    return run(["crontab", "-"], input="\n".join(lines) + "\n", capture_output=True, text=True).returncode == 0


def crontab(run=subprocess.run):
    r = run(["crontab", "-l"], capture_output=True, text=True)
    return r.stdout.splitlines() if r.returncode == 0 else []


def remove(system=None, run=subprocess.run):
    system = system or platform.system()
    if system == "Windows":
        return run(["schtasks", "/Delete", "/TN", TASK, "/F"], capture_output=True, text=True).returncode == 0
    if system == "Darwin":
        run(["launchctl", "unload", "-w", str(PLIST)], capture_output=True)
        PLIST.unlink(missing_ok=True)
        return True
    lines = [ln for ln in crontab(run) if MARK not in ln]
    return run(["crontab", "-"], input="\n".join(lines) + "\n", capture_output=True, text=True).returncode == 0


def status(system=None, run=subprocess.run):
    """True when the operating system will start the daily run by itself."""
    system = system or platform.system()
    try:
        if system == "Windows":
            return run(["schtasks", "/Query", "/TN", TASK], capture_output=True, text=True).returncode == 0
        if system == "Darwin":
            return PLIST.exists()
        return any(MARK in ln for ln in crontab(run))
    except OSError:  # no scheduler command on this machine
        return False


def main(argv):
    cmd = argv[0] if argv else "status"
    if cmd == "install":
        at = argv[1] if len(argv) > 1 else "07:30"
        print(f"daily run scheduled at {at}" if install(at) else "could not create the scheduled task")
    elif cmd == "remove":
        print("daily run removed" if remove() else "could not remove the scheduled task")
    else:
        print("scheduled by the system" if status() else "not scheduled: runs only while the app is open")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
