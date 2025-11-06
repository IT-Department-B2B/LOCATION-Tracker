#!/usr/bin/env bash

# Set error handling and environment variable for the port
set -o errexit
PORT=${PORT:-8000} 

# --- Activate the virtual environment ---
source ./.venv/bin/activate

# --- Run the application with explicit host/port settings ---
gunicorn app:app --bind 0.0.0.0:$PORT --chdir /opt/render/project/src/