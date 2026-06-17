"""
App Store Ingestion Module.

Fetches reviews from the Apple App Store using the iTunes RSS feed.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import httpx
import structlog
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.config.settings import Settings
from src.ingestion.models import Review, Store

logger = structlog.get_logger(__name__)

# The iTunes RSS feed URL format
# Note: The RSS feed only provides up to 500 most recent reviews (10 pages of 50).
RSS_URL_TEMPLATE = "https://itunes.apple.com/rss/customerreviews/page={page}/id={app_id}/sortBy=mostRecent/json"


class AppStoreIngestor:
    """Ingestor for Apple App Store reviews."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    @retry(
        retry=retry_if_exception_type((httpx.RequestError, httpx.HTTPStatusError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=2, max=10),
        reraise=True,
    )
    async def _fetch_page(self, client: httpx.AsyncClient, app_id: str, page: int) -> dict[str, Any]:
        """Fetch a single page of reviews with retries."""
        url = RSS_URL_TEMPLATE.format(page=page, app_id=app_id)
        logger.debug("fetching_appstore_page", url=url, page=page)

        response = await client.get(url, timeout=10.0)
        response.raise_for_status()

        data = response.json()
        if not isinstance(data, dict):
            return {}
        return data

    def _parse_review(self, entry: dict[str, Any], app_id: str, product_slug: str) -> Review | None:
        """Parse a raw JSON entry into a Review model."""
        try:
            review_id = entry["id"]["label"]
            author = entry["author"]["name"]["label"]
            title = entry["title"]["label"]
            body = entry["content"]["label"]
            rating = int(entry["im:rating"]["label"])
            version = entry["im:version"]["label"]

            # The date in RSS is ISO8601 like: "2023-11-23T06:56:06-07:00"
            date_str = entry["updated"]["label"]
            date_obj = datetime.fromisoformat(date_str)
            # Convert to UTC if it has timezone info
            if date_obj.tzinfo:
                date_obj = date_obj.astimezone(UTC)

            # Ensure rating is 1-5
            rating = max(1, min(5, rating))

            raw_length = len(body)

            review = Review(
                id=Review.generate_id(Store.APPSTORE, app_id, review_id),
                store=Store.APPSTORE,
                product=product_slug,
                author=author,
                rating=rating,
                title=title,
                body=body,
                date=date_obj,
                version=version,
                raw_length=raw_length,
            )
            return review

        except (KeyError, ValueError, TypeError) as e:
            logger.warning("failed_to_parse_appstore_entry", error=str(e), entry_id=entry.get("id", {}).get("label"))
            return None

    async def fetch_reviews(
        self, product_slug: str, app_id: str, window_start: datetime
    ) -> list[Review]:
        """
        Fetch reviews for a given app ID, filtering by date window.

        Stops paginating when reviews get older than `window_start`.
        """
        if not app_id:
            logger.info("appstore_skip", reason="no_app_id", product=product_slug)
            return []

        reviews: list[Review] = []
        page = 1
        max_pages = 10  # iTunes RSS only goes up to page 10

        # Ensure window_start is timezone-aware
        if window_start.tzinfo is None:
            window_start = window_start.replace(tzinfo=UTC)

        logger.info(
            "appstore_fetch_start",
            product=product_slug,
            app_id=app_id,
            window_start=window_start.isoformat(),
        )

        async with httpx.AsyncClient() as client:
            while page <= max_pages:
                try:
                    data = await self._fetch_page(client, app_id, page)
                except httpx.HTTPError as e:
                    logger.error("appstore_fetch_error", error=str(e), product=product_slug)
                    break

                feed = data.get("feed", {})
                entries = feed.get("entry")

                # If there are no entries, or it's a single entry dict instead of list
                if not entries:
                    break
                if isinstance(entries, dict):
                    entries = [entries]

                page_reviews = []
                oldest_date = datetime.now(UTC)

                for entry in entries:
                    rev = self._parse_review(entry, app_id, product_slug)
                    if rev:
                        page_reviews.append(rev)
                        if rev.date < oldest_date:
                            oldest_date = rev.date

                # Filter by date window
                valid_reviews = [r for r in page_reviews if r.date >= window_start]
                reviews.extend(valid_reviews)

                logger.debug(
                    "appstore_page_processed",
                    page=page,
                    fetched=len(page_reviews),
                    valid=len(valid_reviews),
                )

                # If we've hit reviews older than our window, stop paginating
                if oldest_date < window_start:
                    logger.debug("appstore_window_reached", oldest_date=oldest_date.isoformat())
                    break

                # If we've hit our total max reviews limit, stop
                if len(reviews) >= self.settings.max_reviews_per_product:
                    logger.debug("appstore_max_reviews_reached")
                    # Truncate just in case
                    reviews = reviews[:self.settings.max_reviews_per_product]
                    break

                page += 1

        logger.info("appstore_fetch_complete", product=product_slug, count=len(reviews))
        return reviews
