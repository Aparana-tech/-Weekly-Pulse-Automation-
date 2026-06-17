"""
Settings — Configuration loader for the Pulse pipeline.

Configuration is loaded in order (later overrides earlier):
  1. config/default.yaml          — Base defaults
  2. config/{PULSE_ENV}.yaml      — Environment-specific overrides
  3. Environment variables         — PULSE_* prefix
  4. .env file                     — Local overrides (gitignored)
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

import yaml
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _find_project_root() -> Path:
    """Walk up from this file to find the project root (contains pyproject.toml)."""
    current = Path(__file__).resolve().parent
    for _ in range(10):
        if (current / "pyproject.toml").exists():
            return current
        current = current.parent
    # Fallback: assume CWD
    return Path.cwd()


PROJECT_ROOT = _find_project_root()
CONFIG_DIR = PROJECT_ROOT / "config"


def _load_yaml_config() -> dict:
    """Load base YAML config, then overlay environment-specific YAML if present."""
    merged: dict = {}

    # 1. Load default.yaml
    default_path = CONFIG_DIR / "default.yaml"
    if default_path.exists():
        with open(default_path) as f:
            data = yaml.safe_load(f)
            if isinstance(data, dict):
                merged.update(data)

    # 2. Load environment-specific override (e.g., config/development.yaml)
    env_name = os.getenv("PULSE_ENV", "").strip()
    if env_name:
        env_path = CONFIG_DIR / f"{env_name}.yaml"
        if env_path.exists():
            with open(env_path) as f:
                data = yaml.safe_load(f)
                if isinstance(data, dict):
                    merged.update(data)

    return merged


class Settings(BaseSettings):
    """
    Pipeline configuration settings.

    Values are resolved in order: YAML defaults → env vars → .env file.
    All environment variables use the ``PULSE_`` prefix.
    """

    model_config = SettingsConfigDict(
        env_prefix="PULSE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Environment
    env: str = Field(default="development", description="Environment: development or production")

    # --- Ingestion ---
    use_presidio_ner: bool = Field(
        default=False,
        description="Whether to use Microsoft Presidio for advanced NER-based name scrubbing (requires presidio-analyzer and presidio-anonymizer).",
    )
    review_window_weeks: int = Field(
        default=10,
        ge=1,
        le=52,
        description="Rolling window in weeks for review ingestion (8-12 recommended).",
    )
    max_reviews_per_product: int = Field(
        default=500,
        ge=1,
        description="Cap on reviews ingested per product per run.",
    )

    # --- Analysis ---
    min_cluster_size: int = Field(
        default=5,
        ge=2,
        description="Minimum reviews for HDBSCAN to form a cluster.",
    )
    max_themes: int = Field(
        default=5,
        ge=1,
        description="Maximum themes to include in the report.",
    )
    quotes_per_theme: int = Field(
        default=3,
        ge=1,
        description="Maximum verbatim quotes per theme.",
    )
    actions_per_theme: int = Field(
        default=2,
        ge=1,
        description="Maximum action ideas per theme.",
    )

    # --- Analysis & Intelligence ---
    llm_model: str = Field(
        default="llama-3.3-70b-versatile",
        description="LLM model to use for summarization and theme extraction (e.g., llama-3.3-70b-versatile, gpt-4o-mini)",
    )
    embedding_model: str = Field(
        default="all-MiniLM-L6-v2", description="Embedding model to use for clustering"
    )
    max_tokens_per_run: int = Field(
        default=60000,
        ge=1000,
        description="Hard token budget per pipeline run.",
    )

    # --- Delivery ---
    email_mode: Literal["draft", "send"] = Field(
        default="draft",
        description="Email delivery mode: 'draft' creates drafts only, 'send' sends immediately.",
    )

    # --- Cost Controls ---
    cost_alert_threshold_usd: float = Field(
        default=2.00,
        ge=0.0,
        description="Warn if a single run exceeds this USD cost.",
    )

    # --- Retry ---
    retry_max_attempts: int = Field(
        default=3,
        ge=1,
        description="Max retries for transient failures.",
    )
    retry_backoff_base_sec: int = Field(
        default=2,
        ge=1,
        description="Exponential backoff base in seconds.",
    )

    # --- State ---
    run_ledger_path: str = Field(
        default="./data/run_ledger.json",
        description="Path to the run ledger JSON file.",
    )

    # --- Logging ---
    log_level: str = Field(
        default="INFO",
        description="Logging verbosity (DEBUG, INFO, WARNING, ERROR).",
    )

    # --- Secrets ---
    openai_api_key: str = Field(default="", description="OpenAI API Key")
    groq_api_key: str = Field(default="", description="Groq API Key")

    @field_validator("log_level")
    @classmethod
    def _normalize_log_level(cls, v: str) -> str:
        v = v.upper().strip()
        valid = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if v not in valid:
            raise ValueError(f"log_level must be one of {valid}, got '{v}'")
        return v


def load_settings(**overrides: object) -> Settings:
    """
    Create a Settings instance by merging YAML config with env vars.

    Parameters
    ----------
    **overrides
        Explicit keyword overrides (highest priority). Useful for tests.

    Returns
    -------
    Settings
        Fully resolved configuration.
    """
    yaml_config = _load_yaml_config()
    # Merge: YAML provides defaults, overrides are highest priority
    merged = {**yaml_config, **overrides}
    return Settings(**merged)  # type: ignore[arg-type]
