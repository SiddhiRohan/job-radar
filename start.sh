#!/bin/sh
# Start job radar: ./start.sh (Linux) or double-click start.command (macOS). Keep the window open while you use it.
cd "$(dirname "$0")" || exit 1
for py in python3 python; do
  if command -v "$py" >/dev/null 2>&1; then exec "$py" start.py "$@"; fi
done
echo "Python 3.11 or newer is needed: https://www.python.org/downloads/"
exit 1
