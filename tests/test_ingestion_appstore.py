"""
Tests for App Store Ingestion Module.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from src.config.settings import Settings
from src.ingestion.appstore import AppStoreIngestor
from src.ingestion.models import Store


@pytest.fixture
def settings() -> Settings:
    return Settings()


@pytest.fixture
def ingestor(settings: Settings) -> AppStoreIngestor:
    return AppStoreIngestor(settings)


class TestAppStoreIngestor:
    """Test AppStoreIngestor logic."""

    def test_parse_review_valid(self, ingestor: AppStoreIngestor) -> None:
        raw_entry = {
            "id": {"label": "123456789"},
            "author": {"name": {"label": "John Doe"}},
            "title": {"label": "Great App"},
            "content": {"label": "I really like this app."},
            "im:rating": {"label": "5"},
            "im:version": {"label": "1.0.0"},
            "updated": {"label": "2026-06-15T12:00:00-07:00"},
        }

        review = ingestor._parse_review(raw_entry, "app_123", "test_app")

        assert review is not None
        assert review.store == Store.APPSTORE
        assert review.author == "John Doe"
        assert review.title == "Great App"
        assert review.body == "I really like this app."
        assert review.rating == 5
        assert review.version == "1.0.0"
        assert review.raw_length == len("I really like this app.")
        assert review.date.tzinfo == UTC

    def test_parse_review_invalid(self, ingestor: AppStoreIngestor) -> None:
        raw_entry = {"id": {"label": "123456789"}}  # Missing required fields
        review = ingestor._parse_review(raw_entry, "app_123", "test_app")
        assert review is None

    @pytest.mark.asyncio
    async def test_fetch_reviews_no_app_id(self, ingestor: AppStoreIngestor) -> None:
        reviews = await ingestor.fetch_reviews("test_app", "", datetime.now(UTC))
        assert reviews == []

    @pytest.mark.asyncio
    async def test_fetch_reviews_mock_http(self, ingestor: AppStoreIngestor, httpx_mock) -> None:
        # Mock the HTTP response for page 1
        httpx_mock.add_response(
            url="https://itunes.apple.com/rss/customerreviews/page=1/id=123/sortBy=mostRecent/json",
            json={
                "feed": {
                    "entry": [
                        {
                            "id": {"label": "1"},
                            "author": {"name": {"label": "User A"}},
                            "title": {"label": "Title A"},
                            "content": {"label": "Body A"},
                            "im:rating": {"label": "4"},
                            "im:version": {"label": "1.1"},
                            "updated": {"label": datetime.now(UTC).isoformat()},
                        }
                    ]
                }
            }
        )
        # Mock page 2 with no entries so pagination stops
        httpx_mock.add_response(
            url="https://itunes.apple.com/rss/customerreviews/page=2/id=123/sortBy=mostRecent/json",
            json={"feed": {}}
        )

        window_start = datetime.now(UTC) - timedelta(days=1)
        reviews = await ingestor.fetch_reviews("test_app", "123", window_start)

        assert len(reviews) == 1
        assert reviews[0].author == "User A"
