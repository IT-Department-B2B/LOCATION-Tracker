#!/usr/bin/env bash

# Exit immediately if a command exits with a non-zero status
set -o errexit

# --- Activate the virtual environment ---
# This ensures Gunicorn is in the PATH
# We try both common venv paths to be robust
if [ -f "./.venv/bin/activate" ]; then
    source ./.venv/bin/activate
else
    # Fallback path (common on Render/similar hosts)
    source /opt/render/project/src/.venv/bin/activate
fi

# --- Run the application using the simple command ---
# Gunicorn is now guaranteed to be in the PATH
gunicorn app:app