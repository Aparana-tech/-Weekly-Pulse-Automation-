"""
Play Store Ingestion Module.

Fetches reviews from the Google Play Store using the google-play-scraper library.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

import structlog
from google_play_scraper import Sort, reviews
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.config.settings import Settings
from src.ingestion.models import Review, Store

logger = structlog.get_logger(__name__)


class PlayStoreIngestor:
    """Ingestor for Google Play Store reviews."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    @retry(
        retry=retry_if_exception_type(Exception),  # scraper can throw various exceptions
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=2, max=10),
        reraise=True,
    )
    async def _fetch_batch(
        self, package_name: str, count: int, continuation_token: str | None = None
    ) -> tuple[list[dict], str | None]:
        """
        Fetch a batch of reviews.
        Note: google-play-scraper is synchronous, so we run it in a thread.
        """
        # Run synchronous scraper in executor
        loop = asyncio.get_running_loop()

        def _scrape() -> tuple[list[dict], str | None]:
            return reviews(  # type: ignore[no-any-return]
                package_name,
                lang="en",
                country="in",  # Default to India for fintech apps
                sort=Sort.NEWEST,
                count=count,
                continuation_token=continuation_token,
            )

        result, new_token = await loop.run_in_executor(None, _scrape)
        return result, new_token

    def _parse_review(self, entry: dict, package_name: str, product_slug: str) -> Review | None:
        """Parse a scraper result dictionary into a Review model."""
        try:
            review_id = entry.get("reviewId")
            if not review_id:
                return None

            author = entry.get("userName", "Unknown")
            body = entry.get("content", "")
            rating = int(entry.get("score", 0))
            version = entry.get("reviewCreatedVersion")

            # Date comes back as a datetime object
            date_obj = entry.get("at")
            if not isinstance(date_obj, datetime):
                return None

            # Convert to UTC
            if date_obj.tzinfo is None:
                date_obj = date_obj.replace(tzinfo=UTC)
            else:
                date_obj = date_obj.astimezone(UTC)

            rating = max(1, min(5, rating))
            raw_length = len(body)

            review = Review(
                id=Review.generate_id(Store.PLAYSTORE, package_name, review_id),
                store=Store.PLAYSTORE,
                product=product_slug,
                author=author,
                rating=rating,
                title=None,  # Play Store scraper doesn't provide titles
                body=body,
                date=date_obj,
                version=version,
                raw_length=raw_length,
            )
            return review

        except Exception as e:
            logger.warning("failed_to_parse_playstore_entry", error=str(e), review_id=entry.get("reviewId"))
            return None

    async def fetch_reviews(
        self, product_slug: str, package_name: str, window_start: datetime
    ) -> list[Review]:
        """
        Fetch reviews for a given package name, filtering by date window.
        """
        if not package_name:
            logger.info("playstore_skip", reason="no_package_name", product=product_slug)
            return []

        all_reviews: list[Review] = []
        continuation_token = None
        batch_size = 100

        # Ensure window_start is timezone-aware
        if window_start.tzinfo is None:
            window_start = window_start.replace(tzinfo=UTC)

        logger.info(
            "playstore_fetch_start",
            product=product_slug,
            package_name=package_name,
            window_start=window_start.isoformat(),
        )

        while True:
            try:
                data, continuation_token = await self._fetch_batch(
                    package_name, batch_size, continuation_token
                )
            except Exception as e:
                logger.error("playstore_fetch_error", error=str(e), product=product_slug)
                break

            if not data:
                break

            batch_reviews = []
            oldest_date = datetime.now(UTC)

            for entry in data:
                rev = self._parse_review(entry, package_name, product_slug)
                if rev:
                    batch_reviews.append(rev)
                    if rev.date < oldest_date:
                        oldest_date = rev.date

            # Filter by date window
            valid_reviews = [r for r in batch_reviews if r.date >= window_start]
            all_reviews.extend(valid_reviews)

            logger.debug(
                "playstore_batch_processed",
                fetched=len(batch_reviews),
                valid=len(valid_reviews),
                total=len(all_reviews),
            )

            # If we've hit reviews older than our window, stop paginating
            if oldest_date < window_start:
                logger.debug("playstore_window_reached", oldest_date=oldest_date.isoformat())
                break

            # If we've hit our total max reviews limit, stop
            if len(all_reviews) >= self.settings.max_reviews_per_product:
                logger.debug("playstore_max_reviews_reached")
                all_reviews = all_reviews[:self.settings.max_reviews_per_product]
                break

            # If there's no more data, stop
            if continuation_token is None:
                break

        logger.info("playstore_fetch_complete", product=product_slug, count=len(all_reviews))
        return all_reviews
