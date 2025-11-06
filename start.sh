#!/usr/bin/env bash

# Exit immediately if a command exits with a non-zero status
set -o errexit

# --- Activate the virtual environment ---
# This ensures Gunicorn is found in the PATH
source ./.venv/bin/activate

# --- Run the application using the simple command ---
gunicorn app:app
