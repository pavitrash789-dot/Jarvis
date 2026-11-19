#!/bin/bash
# JARVIS launcher script
set -e
cd "$(dirname "$0")"

SCRIPT_DIR="$(pwd)"

if [ -f "$SCRIPT_DIR/venv/bin/python" ]; then
    echo "🚀 Starting JARVIS with virtualenv python..."
    exec "$SCRIPT_DIR/venv/bin/python" "$SCRIPT_DIR/jarvis.py" "$@"
elif [ -d "$SCRIPT_DIR/venv" ]; then
    echo "🚀 Activating virtualenv and running JARVIS..."
    source "$SCRIPT_DIR/venv/bin/activate"
    exec python3 "$SCRIPT_DIR/jarvis.py" "$@"
else
    echo "🚀 Running JARVIS with system python3..."
    exec python3 "$SCRIPT_DIR/jarvis.py" "$@"
fi

