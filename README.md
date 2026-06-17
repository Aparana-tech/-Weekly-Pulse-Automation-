# 📊 Pulse — Automated Weekly App Review Pulse

> Transforms public App Store & Google Play reviews for fintech products into weekly insight reports, delivered through Google Workspace via MCP.

## Overview

Pulse is an automated pipeline that:

1. **Ingests** public reviews from Apple App Store (RSS) and Google Play (scraper) for selected fintech products
2. **Clusters & analyzes** feedback using embeddings (UMAP + HDBSCAN) and LLM summarization
3. **Renders** concise one-page reports with themes, real user quotes, and action ideas
4. **Delivers** via MCP servers to Google Docs (append weekly sections) and Gmail (stakeholder notifications)

### Supported Products

| Product | Category |
|---------|----------|
| INDMoney | Wealth & Investment Management |
| Groww | Stock & Mutual Fund Trading |
| PowerUp Money | Personal Finance |
| Wealth Monitor | Portfolio Tracking |
| Kuvera | Direct Mutual Fund Investing |

## Quick Start

### Prerequisites

- Python 3.11+
- pip

### Installation

```bash
# Clone the repository
git clone <repo-url> && cd pulse

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install with all dependencies
make install-dev

# Copy environment template
cp .env.example .env
# Edit .env with your API keys
```

### Usage

```bash
# Run pulse for a specific product (current week)
pulse run --product groww

# Run for a specific ISO week (backfill)
pulse run --product groww --week 2026-W23

# Run for all products
pulse run --all

# Dry run (no delivery)
pulse run --product groww --dry-run

# Check run status
pulse status --product groww --week 2026-W23

# View run history
pulse history --product groww --limit 10
```

### Development

```bash
make lint          # Run linter
make format        # Auto-format code
make typecheck     # Run type checker
make test          # Run tests
make test-cov      # Run tests with coverage
```

## Architecture

The system follows a layered architecture with MCP-first delivery:

```
Data Sources → Ingestion → Analysis → Rendering → MCP Delivery
                  ↓                                    ↓
             PII Scrubber                    Google Docs + Gmail
```

See [docs/architecture.md](docs/architecture.md) for full details.

## Documentation

| Document | Description |
|----------|-------------|
| [Problem Statement](docs/problemstatement.md) | What we're building and why |
| [Architecture](docs/architecture.md) | System design, components, data models |
| [Implementation Plan](docs/implementation_plan.md) | Phase-wise build plan |

## Configuration

Configuration is loaded in this order (later overrides earlier):

1. `config/default.yaml` — Base defaults
2. Environment-specific YAML — `config/{PULSE_ENV}.yaml`
3. Environment variables — `PULSE_*` prefix
4. `.env` file — Local overrides (gitignored)

See [.env.example](.env.example) for all available settings.

## Project Structure

```
pulse/
├── docs/                    # Documentation
├── src/                     # Source code
│   ├── main.py              # CLI entry point
│   ├── orchestrator.py      # Pipeline controller
│   ├── ingestion/           # App Store + Play Store scrapers
│   ├── analysis/            # Embeddings, clustering, LLM
│   ├── rendering/           # Docs + email renderers
│   ├── delivery/            # MCP client + delivery modules
│   ├── state/               # Run ledger + idempotency
│   └── config/              # Settings loader
├── config/                  # Configuration files
├── tests/                   # Test suite
├── data/                    # Runtime data (gitignored)
└── logs/                    # Log output (gitignored)
```

## License

MIT
