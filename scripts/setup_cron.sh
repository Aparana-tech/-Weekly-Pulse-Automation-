#!/usr/bin/env bash
# Pulse Cron Setup Script
#
# Adds a weekly cron job to run the Pulse pipeline every Monday at 6:00 AM.
# It automatically sets PULSE_ENV=production.

set -e

# Define the command
PROJECT_DIR="$(pwd)"
VENV_PYTHON="$PROJECT_DIR/.venv/bin/python"
CRON_SCHEDULE="0 6 * * 1" # Every Monday at 6:00 AM
LOG_FILE="$PROJECT_DIR/logs/cron.log"

if [ ! -f "$VENV_PYTHON" ]; then
    echo "Error: Python virtual environment not found at $VENV_PYTHON"
    exit 1
fi

mkdir -p "$PROJECT_DIR/logs"

# The cron command
CRON_CMD="cd '$PROJECT_DIR' && PULSE_ENV=production '$VENV_PYTHON' -m pulse run --all --force >> '$LOG_FILE' 2>&1"

# Create a temporary file for the current crontab
TMP_CRON=$(mktemp)

# Read current crontab, ignoring errors if it doesn't exist
crontab -l > "$TMP_CRON" 2>/dev/null || true

# Check if the job already exists
if grep -q "pulse run --all" "$TMP_CRON"; then
    echo "Pulse cron job already exists!"
    cat "$TMP_CRON"
else
    # Append the new job
    echo "$CRON_SCHEDULE $CRON_CMD" >> "$TMP_CRON"
    crontab "$TMP_CRON"
    echo "Successfully installed Pulse cron job:"
    echo "$CRON_SCHEDULE $CRON_CMD"
fi

rm "$TMP_CRON"
