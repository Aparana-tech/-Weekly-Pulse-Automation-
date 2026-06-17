"""
Ingestion Pipeline.

Wires together App Store ingestion, Play Store ingestion, merging, deduplication,
and PII scrubbing into a single `ingest_reviews` function.
"""

from __future__ import annotations

import asyncio
from datetime import datetime

import structlog

from src.config.product_registry import ProductRegistry
from src.config.settings import Settings
from src.ingestion.appstore import AppStoreIngestor
from src.ingestion.merger import merge_and_deduplicate
from src.ingestion.models import Review
from src.ingestion.pii_scrubber import PIIScrubber
from src.ingestion.playstore import PlayStoreIngestor

logger = structlog.get_logger(__name__)


async def ingest_reviews(
    product_slug: str,
    window_start: datetime,
    settings: Settings,
    registry: ProductRegistry,
) -> list[Review]:
    """
    Execute the full ingestion pipeline for a given product.

    1. Fetch reviews from App Store and Play Store concurrently.
    2. Merge and deduplicate them.
    3. Truncate to the max_reviews cap.
    4. Scrub PII from the results.

    Parameters
    ----------
    product_slug
        The URL-safe slug of the product to ingest.
    window_start
        The oldest datetime to fetch reviews for.
    settings
        Pipeline settings.
    registry
        Product registry to look up app IDs.

    Returns
    -------
    list[Review]
        A clean, deduplicated, PII-scrubbed list of reviews, sorted newest-first.
    """
    logger.info("ingestion_pipeline_started", product=product_slug)

    product = registry.get_or_raise(product_slug)
    appstore = AppStoreIngestor(settings)
    playstore = PlayStoreIngestor(settings)
    scrubber = PIIScrubber(use_presidio=settings.use_presidio_ner)

    # Run fetches concurrently
    appstore_task = asyncio.create_task(
        appstore.fetch_reviews(product_slug, product.appstore_id, window_start)
    )
    playstore_task = asyncio.create_task(
        playstore.fetch_reviews(product_slug, product.playstore_id, window_start)
    )

    # Wait for both to complete
    # return_exceptions=True prevents one failure from killing the other
    results = await asyncio.gather(appstore_task, playstore_task, return_exceptions=True)

    appstore_reviews: list[Review] = []
    playstore_reviews: list[Review] = []

    if isinstance(results[0], Exception):
        logger.error(
            "appstore_fetch_failed_gracefully",
            error=str(results[0]),
            product=product_slug
        )
    elif isinstance(results[0], list):
        appstore_reviews = results[0]

    if isinstance(results[1], Exception):
        logger.error(
            "playstore_fetch_failed_gracefully",
            error=str(results[1]),
            product=product_slug
        )
    elif isinstance(results[1], list):
        playstore_reviews = results[1]

    # Merge and deduplicate
    merged_reviews = merge_and_deduplicate(
        appstore_reviews=appstore_reviews,
        playstore_reviews=playstore_reviews,
        settings=settings,
    )

    # Scrub PII
    clean_reviews = scrubber.scrub_reviews(merged_reviews)

    # Filter out reviews that contain no alphabetical characters (e.g. emoji-only)
    clean_reviews = [r for r in clean_reviews if any(c.isalpha() for c in r.body)]

    logger.info(
        "ingestion_pipeline_completed",
        product=product_slug,
        total_clean_reviews=len(clean_reviews),
    )

    return clean_reviews
