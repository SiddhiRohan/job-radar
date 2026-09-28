"""Start job radar. Uses only the standard library, so it runs before anything is installed.

    Windows: double-click start.bat      macOS: double-click start.command      Linux: ./start.sh

It checks Python, creates a private environment in .venv the first time, installs the packages again only when
requirements.txt changes, copies .env.example to .env when there is none, runs the doctor, and opens the app at
http://localhost:8000. When the app is already running it just opens the browser."""

import hashlib
import os
import shutil
import socket
import subprocess
import sys
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENV = ROOT / ".venv"
PY = VENV / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
STAMP = VENV / ".requirements.sha256"
PORT = int(os.environ.get("RADAR_PORT", "8000"))  # set RADAR_PORT when 8000 is taken
URL = f"http://localhost:{PORT}"


def say(msg):
    print(msg, flush=True)


def running(port=PORT):
    with socket.socket() as s:
        s.settimeout(0.3)
        return s.connect_ex(("127.0.0.1", port)) == 0


def prepare():
    """Create .venv and install requirements when they changed. Returns the Python to run the app with."""
    if not PY.exists():
        say("First start: making a private Python environment in .venv (about a minute)...")
        subprocess.check_call([sys.executable, "-m", "venv", str(VENV)])
    want = hashlib.sha256((ROOT / "requirements.txt").read_bytes()).hexdigest()
    if not STAMP.exists() or STAMP.read_text(encoding="utf-8").strip() != want:
        say("Installing the packages the app needs...")
        pip = [str(PY), "-m", "pip", "install", "--disable-pip-version-check", "-q", "-r", "requirements.txt"]
        subprocess.check_call(pip, cwd=ROOT)
        STAMP.write_text(want, encoding="utf-8")
    return PY


def main():
    os.chdir(ROOT)
    if sys.version_info < (3, 11):
        say(
            f"Job radar needs Python 3.11 or newer (this is {sys.version.split()[0]}): https://www.python.org/downloads/"
        )
        return 1
    if running():
        say(f"Job radar is already running; opening {URL}")
        webbrowser.open(URL)
        return 0
    try:
        py = prepare()
    except (subprocess.CalledProcessError, OSError) as e:
        say(f"Setup stopped: {e}\nCheck the internet connection and start again.")
        return 1
    if not (ROOT / ".env").exists() and (ROOT / ".env.example").exists():
        shutil.copy(ROOT / ".env.example", ROOT / ".env")
        say("Made .env from .env.example; add your Anthropic API key there, or on the setup page.")
    subprocess.call([str(py), "-m", "radar.doctor", "--brief"])
    say(f"Opening job radar at {URL}. Keep this window open while you use it; close it to stop.")
    return subprocess.call([str(py), "server.py"])


if __name__ == "__main__":
    sys.exit(main())
