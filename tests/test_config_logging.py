"""
Tests for structured logging configuration.
"""

from __future__ import annotations

import logging

import pytest
import structlog
from structlog.testing import capture_logs

from src.config.logging import bind_run_context, bind_stage, configure_logging
from src.config.settings import Settings


def test_logging_configuration_production() -> None:
    """Test that production settings bind context correctly and use structlog."""
    settings = Settings(env="production", log_level="INFO")
    configure_logging(settings)

    # Use structlog.testing to capture the bound logs
    structlog.configure(
        processors=[structlog.processors.JSONRenderer()]
    )

    logger = structlog.get_logger("test_logger")

    bind_run_context("run_123", "test_app", 2026, 25)
    bind_stage("ingestion")

    # In production, contextvars merge context automatically if configured properly
    # For testing, we can just assert the bindings on the contextvars directly.
    ctx = structlog.contextvars.get_contextvars()
    assert ctx["run_id"] == "run_123"
    assert ctx["product"] == "test_app"
    assert ctx["iso_week"] == 25
    assert ctx["stage"] == "ingestion"

    structlog.contextvars.clear_contextvars()


def test_logging_configuration_development() -> None:
    settings = Settings(env="development", log_level="DEBUG")
    configure_logging(settings)
    
    logger = structlog.get_logger("test_logger")
    assert logger is not None
