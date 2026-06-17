# Pulse Operational Runbook

Welcome to the Operational Runbook for the **Pulse Weekly App Review Pipeline**. This document outlines standard operating procedures for maintaining the system, troubleshooting issues, and scaling.

---

## 1. System Architecture Overview

Pulse is a Python CLI backend and React/Vite web dashboard that automates the collection, clustering (UMAP/HDBSCAN), and LLM summarization of app reviews.

- **Data Ledger**: `.pulse_ledger.json` tracks all historical pipeline runs.
- **Config**: `config/products.json` maps apps to their store IDs.
- **Environment**: Configuration is governed by `PULSE_ENV` and overridden by `.env`.
- **Delivery**: Summaries are pushed via local MCP servers (`gmail-cloud` & `google-docs`).

---

## 2. Managing Environments

Pulse supports three distinct modes of operation, defined by `PULSE_ENV`:

| `PULSE_ENV`  | Config File | LLM Model | Email Mode | Max Reviews | Purpose |
|--------------|-------------|-----------|------------|-------------|---------|
| `development`| `development.yaml`| `gpt-4o-mini` | `draft` | 50 | Fast local testing, cheap token usage. |
| `staging`    | `staging.yaml`    | `gpt-4o`      | `draft` | 200 | UAT and LLM prompt testing. |
| `production` | `production.yaml` | `gpt-4o`      | `send`  | 500 | Weekly live runs (via Cron). |

**To test locally without sending emails:**
```bash
PULSE_ENV=development pulse run --product groww
```

---

## 3. Scheduled Execution (Cron)

The pipeline is designed to run completely automatically via the system's cron daemon.

**To install the cron job:**
```bash
./scripts/setup_cron.sh
```
This adds an entry to your crontab to execute `pulse run --all --force` (in production mode) every Monday at 6:00 AM. Logs are piped to `logs/cron.log`.

**To check cron health:**
```bash
./scripts/health_check.py
```

---

## 4. Recovering from Failures

Pulse is highly idempotent and resilient. It tracks its own state in the `.pulse_ledger.json`.

### 4.1 Transient Failures (e.g., App Store Timeout, LLM timeout)
If the pipeline fails mid-execution, it gracefully saves state and marks the run as `partial`. 
**Resolution**: Simply re-run the pipeline. It will automatically load the cached embeddings from `downloads/` and skip directly to the missing steps.
```bash
PULSE_ENV=production pulse run --product groww
```

### 4.2 MCP Delivery Failure
If the `google-docs` or `gmail` MCP server crashes, the circuit breaker will trip after 3 attempts. The data processing phase is already complete, so no tokens are wasted.
**Resolution**: 
1. Check if the local MCP servers are running.
2. Re-run the pipeline. It will bypass all analysis and jump straight to the delivery payload rendering.

---

## 5. Adding New Products

To track a new app, simply edit `config/products.json`.

```json
{
  "slug": "my-new-app",
  "display_name": "My New App",
  "appstore_id": "123456789",
  "playstore_id": "com.example.app",
  "doc_id": "google_docs_id_here",
  "stakeholder_emails": ["team@example.com"]
}
```
Next Monday, the cron job will automatically pick up the new app and deliver the report.

---

## 6. Manual Backfills

If you need to generate a report for a specific week in the past, use the `--week` parameter.
```bash
PULSE_ENV=production pulse run --product groww --week 2026-W20
```

---

## 7. Monitoring the Web Dashboard

The web dashboard is a Vite React application that provides a beautiful view into the data.
To start the dashboard locally:
```bash
# Terminal 1 - Backend API
uvicorn src.api:app --host 0.0.0.0 --port 8000

# Terminal 2 - Frontend UI
cd dashboard && npm run dev
```
Navigate to `http://localhost:5173`.
