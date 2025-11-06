#!/usr/bin/env bash

# Set error handling and environment variable for the port
set -o errexit
PORT=${PORT:-8000} # Use default 8000 if Render doesn't set it automatically

# --- Activate the virtual environment ---
# This is necessary to put gunicorn into the PATH
source ./.venv/bin/activate

# --- Run the application with explicit host/port settings ---
# --bind 0.0.0.0:$PORT ensures Gunicorn binds to the host Render expects.
# --chdir /opt/render/project/src/ ensures Gunicorn is looking in the right directory.
gunicorn app:app --bind 0.0.0.0:$PORT --chdir /opt/render/project/src/
