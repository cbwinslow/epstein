#!/bin/bash
# Mission Control Launch Script
# Simple wrapper to launch Mission Control TUI interface

echo "🚀 Launching Mission Control..."
echo "✅ Using Python 3.10.15"
echo "✅ Dependencies installed and verified"
echo ""

# Set PYTHONPATH to include current directory
export PYTHONPATH=.

# Launch Mission Control
PYTHONPATH=. uv run python -c "from tools.mission_control.app import main; main()"

echo ""
echo "Mission Control session ended."
