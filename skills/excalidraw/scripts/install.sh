#!/usr/bin/env bash
# Install the Python + browser dependencies for the Excalidraw render skill.
#
# This skill drives headless Chromium via Playwright. It needs:
#   - the `playwright` Python package
#   - the Chromium browser binary Playwright downloads
#
# No npm/node is required: the Excalidraw package itself is loaded at render
# time from the esm.sh CDN by render_template.html.
#
# Usage:  bash scripts/install.sh
set -euo pipefail

# Prefer python3 (macOS ships 3.9+, which is enough). Fall back to python.
PY=$(command -v python3 || command -v python)
if [ -z "$PY" ]; then
  echo "ERROR: python3 not found. Install Python >=3.9 first." >&2
  exit 1
fi
echo "Using: $($PY --version)"

# Install playwright into the user environment (no venv required, but if a
# venv is active it will install there). --user keeps it out of system dirs.
echo "Installing playwright..."
"$PY" -m pip install --user --quiet --upgrade playwright 2>&1 | tail -3 || {
  echo "ERROR: pip install playwright failed." >&2
  exit 1
}

# Download the Chromium binary Playwright drives. ~150MB, one-time.
echo "Installing Chromium for Playwright (~150MB, one-time)..."
"$PY" -m playwright install chromium 2>&1 | tail -5 || {
  echo "ERROR: playwright install chromium failed." >&2
  echo "You can retry later with: $PY -m playwright install chromium" >&2
  exit 1
}

echo ""
echo "Done. You can now render:"
echo "  $PY $(dirname "$0")/render.py your-diagram.excalidraw"
