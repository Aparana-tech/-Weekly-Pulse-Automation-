"""
Tests for Play Store Ingestion Module.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from src.config.settings import Settings
from src.ingestion.models import Store
from src.ingestion.playstore import PlayStoreIngestor


@pytest.fixture
def settings() -> Settings:
    return Settings()


@pytest.fixture
def ingestor(settings: Settings) -> PlayStoreIngestor:
    return PlayStoreIngestor(settings)


class TestPlayStoreIngestor:
    """Test PlayStoreIngestor logic."""

    def test_parse_review_valid(self, ingestor: PlayStoreIngestor) -> None:
        now = datetime.now(UTC)
        raw_entry = {
            "reviewId": "gp_12345",
            "userName": "Jane Smith",
            "content": "Nice design but a bit slow.",
            "score": 3,
            "reviewCreatedVersion": "2.1.0",
            "at": now,
        }

        review = ingestor._parse_review(raw_entry, "com.test.app", "test_app")

        assert review is not None
        assert review.store == Store.PLAYSTORE
        assert review.author == "Jane Smith"
        assert review.title is None
        assert review.body == "Nice design but a bit slow."
        assert review.rating == 3
        assert review.version == "2.1.0"
        assert review.date == now

    def test_parse_review_invalid(self, ingestor: PlayStoreIngestor) -> None:
        raw_entry = {"userName": "Jane"}  # Missing reviewId and date
        review = ingestor._parse_review(raw_entry, "com.test.app", "test_app")
        assert review is None

    @pytest.mark.asyncio
    async def test_fetch_reviews_no_package_name(self, ingestor: PlayStoreIngestor) -> None:
        reviews = await ingestor.fetch_reviews("test_app", "", datetime.now(UTC))
        assert reviews == []

    @pytest.mark.asyncio
    async def test_fetch_reviews_mock_scraper(self, ingestor: PlayStoreIngestor, monkeypatch: pytest.MonkeyPatch) -> None:
        # Mock the scraper function
        now = datetime.now(UTC)

        async def mock_fetch_batch(*args, **kwargs):
            # Return one review and no continuation token
            return [
                {
                    "reviewId": "1",
                    "userName": "User A",
                    "content": "Body A",
                    "score": 4,
                    "reviewCreatedVersion": "1.1",
                    "at": now,
                }
            ], None

        monkeypatch.setattr(ingestor, "_fetch_batch", mock_fetch_batch)

        window_start = now - timedelta(days=1)
        reviews = await ingestor.fetch_reviews("test_app", "com.test", window_start)

        assert len(reviews) == 1
        assert reviews[0].author == "User A"
