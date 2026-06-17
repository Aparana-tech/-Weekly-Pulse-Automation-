#!/usr/bin/env python3
"""
Pulse Health Check

Checks the Run Ledger for the latest runs and returns a non-zero exit code
if any of the latest runs failed. Useful for monitoring integrations (e.g., Datadog, PagerDuty).
"""

import json
import sys
from pathlib import Path

def main():
    ledger_path = Path(".pulse_ledger.json")
    if not ledger_path.exists():
        print("No run ledger found. System healthy (no runs attempted).")
        sys.exit(0)

    try:
        with open(ledger_path, "r") as f:
            runs = json.load(f)
    except Exception as e:
        print(f"CRITICAL: Failed to parse ledger - {e}")
        sys.exit(1)

    if not runs:
        print("Run ledger is empty. System healthy.")
        sys.exit(0)

    # Sort by started_at descending
    runs.sort(key=lambda x: x.get("started_at", ""), reverse=True)
    
    # Check the most recent run
    latest_run = runs[0]
    status = latest_run.get("status", "unknown")
    run_id = latest_run.get("run_id", "unknown")
    
    if status == "failed":
        print(f"CRITICAL: Latest run ({run_id}) failed.")
        sys.exit(2)
    elif status == "partial":
        print(f"WARNING: Latest run ({run_id}) partially failed (likely a delivery issue).")
        # Depending on monitoring, you might want this to be an error (exit 1) or just a warning (exit 0)
        sys.exit(0)
    elif status == "running":
        print(f"INFO: A run ({run_id}) is currently in progress.")
        sys.exit(0)
    elif status == "completed":
        print(f"OK: Latest run ({run_id}) completed successfully.")
        sys.exit(0)
    else:
        print(f"UNKNOWN: Unrecognized status '{status}' for run {run_id}.")
        sys.exit(3)

if __name__ == "__main__":
    main()
