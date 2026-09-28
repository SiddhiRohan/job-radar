#!/bin/sh
# Start job radar: ./start.sh (Linux) or double-click start.command (macOS). Keep the window open while you use it.
# Picks the first Python that is 3.11 or newer: macOS's own python3 is often older than one installed from python.org.
cd "$(dirname "$0")" || exit 1
for py in python3.14 python3.13 python3.12 python3.11 python3 python; do
  if command -v "$py" >/dev/null 2>&1 && "$py" -c 'import sys; sys.exit(sys.version_info < (3, 11))' 2>/dev/null; then
    exec "$py" start.py "$@"
  fi
done
echo "Python 3.11 or newer is needed: https://www.python.org/downloads/"
exit 1
