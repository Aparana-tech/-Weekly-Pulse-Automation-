"""
Logging Configuration.

Configures structlog to output JSON logs in production, and pretty console logs in development.
Provides helper functions to bind context variables like run_id, product, etc.
"""

from __future__ import annotations

import logging
import sys

import structlog

from src.config.settings import Settings


def configure_logging(settings: Settings) -> None:
    """Configure structlog based on the provided settings."""
    log_level_name = settings.log_level.upper()
    log_level = getattr(logging, log_level_name, logging.INFO)

    # We use structlog.contextvars to allow binding variables like run_id
    # globally within an asyncio context.
    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if settings.env == "production":
        # JSON logging for production (DataDog/CloudWatch friendly)
        processors = shared_processors + [
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(),
        ]
    else:
        # Pretty console logging for development
        processors = shared_processors + [
            structlog.dev.ConsoleRenderer(colors=True),
        ]

    # Configure standard logging to route to structlog
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )

    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def bind_run_context(run_id: str, product: str, iso_year: int, iso_week: int) -> None:
    """Bind global context variables for the current run."""
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(
        run_id=run_id,
        product=product,
        iso_year=iso_year,
        iso_week=iso_week,
    )


def bind_stage(stage: str) -> None:
    """Bind the current pipeline stage."""
    structlog.contextvars.bind_contextvars(stage=stage)
