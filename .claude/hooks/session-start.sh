#!/bin/bash
set -euo pipefail

# Only run in remote Claude Code web sessions
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

echo "NEXUS FinancialModeling: Installing Python dependencies..."

# Install pip dependencies from requirements.txt
pip install --quiet --prefer-binary -r "$CLAUDE_PROJECT_DIR/requirements.txt"

# Install flake8 for linting (not in requirements.txt)
pip install --quiet flake8

# Set PYTHONPATH so scripts can import from project root
echo "export PYTHONPATH=\"$CLAUDE_PROJECT_DIR\"" >> "$CLAUDE_ENV_FILE"

echo "NEXUS FinancialModeling: Session environment ready."
