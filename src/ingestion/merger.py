"""
Review Merger and Deduplicator.

Merges reviews from multiple stores, deduplicates them by ID,
sorts by date, and enforces maximum review limits.
"""

from __future__ import annotations

import structlog

from src.config.settings import Settings
from src.ingestion.models import Review

logger = structlog.get_logger(__name__)


def merge_and_deduplicate(
    appstore_reviews: list[Review],
    playstore_reviews: list[Review],
    settings: Settings,
) -> list[Review]:
    """
    Merge, deduplicate, sort, and truncate review lists.

    Parameters
    ----------
    appstore_reviews
        Reviews fetched from the App Store.
    playstore_reviews
        Reviews fetched from the Play Store.
    settings
        Pipeline settings (provides max_reviews_per_product).

    Returns
    -------
    list[Review]
        Merged and deduplicated reviews, newest first, truncated to limit.
    """
    # Use a dictionary keyed by ID to automatically deduplicate
    # Later items overwrite earlier items if there's an ID collision
    unique_reviews: dict[str, Review] = {}

    for r in appstore_reviews:
        unique_reviews[r.id] = r

    for r in playstore_reviews:
        unique_reviews[r.id] = r

    merged = list(unique_reviews.values())

    # Sort by date descending (newest first)
    merged.sort(key=lambda r: r.date, reverse=True)

    # Enforce global cap
    if len(merged) > settings.max_reviews_per_product:
        merged = merged[:settings.max_reviews_per_product]

    logger.info(
        "reviews_merged",
        appstore_count=len(appstore_reviews),
        playstore_count=len(playstore_reviews),
        total_unique=len(merged),
        limit_applied=settings.max_reviews_per_product,
    )

    return merged
