#!/bin/bash
# Install the Python packages in a new Claude Code cloud container, so the
# tests, the paper runs and the evotrader MCP servers work from the first turn.
# Idempotent: a container that already has them skips the install in seconds.
set -euo pipefail

if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

cd "${CLAUDE_PROJECT_DIR:-$(dirname "$0")/../..}"
python3 -m pip install -q --disable-pip-version-check --root-user-action=ignore -r requirements-research.txt
