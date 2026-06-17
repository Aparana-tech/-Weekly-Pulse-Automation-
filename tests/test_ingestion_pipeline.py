"""
Integration test for the full ingestion pipeline.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from src.config.product_registry import ProductConfig, ProductRegistry
from src.config.settings import Settings
from src.ingestion.models import Store
from src.ingestion.pipeline import ingest_reviews


@pytest.fixture
def settings() -> Settings:
    return Settings(max_reviews_per_product=50)


@pytest.fixture
def registry() -> ProductRegistry:
    return ProductRegistry(
        [
            ProductConfig(
                slug="test_app",
                display_name="Test App",
                appstore_id="12345",
                playstore_id="com.test.app",
            )
        ]
    )


class TestIngestionPipeline:
    """Test the full ingest_reviews pipeline."""

    @pytest.mark.asyncio
    async def test_ingest_reviews_success(
        self, settings: Settings, registry: ProductRegistry, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test the happy path where both fetchers return data."""
        now = datetime.now(UTC)

        # Mock App Store fetcher
        async def mock_appstore_fetch(*args, **kwargs):
            from src.ingestion.models import Review
            return [
                Review(
                    id="a1",
                    store=Store.APPSTORE,
                    product="test_app",
                    author="Alice",
                    rating=5,
                    body="Great app! Call me at 9876543210.",
                    title="Super",
                    date=now - timedelta(days=1),
                )
            ]

        # Mock Play Store fetcher
        async def mock_playstore_fetch(*args, **kwargs):
            from src.ingestion.models import Review
            return [
                Review(
                    id="p1",
                    store=Store.PLAYSTORE,
                    product="test_app",
                    author="Bob",
                    rating=1,
                    body="Terrible app. Email bob@example.com.",
                    title=None,
                    date=now - timedelta(days=2),
                )
            ]

        monkeypatch.setattr("src.ingestion.appstore.AppStoreIngestor.fetch_reviews", mock_appstore_fetch)
        monkeypatch.setattr("src.ingestion.playstore.PlayStoreIngestor.fetch_reviews", mock_playstore_fetch)

        window_start = now - timedelta(days=7)
        reviews = await ingest_reviews("test_app", window_start, settings, registry)

        assert len(reviews) == 2

        # Check sorting (newest first)
        assert reviews[0].id == "a1"
        assert reviews[1].id == "p1"

        # Check PII scrubbing
        assert "9876543210" not in reviews[0].body
        assert "[PHONE]" in reviews[0].body
        assert "bob@example.com" not in reviews[1].body
        assert "[EMAIL]" in reviews[1].body

        # Check author anonymization
        assert reviews[0].author == "[NAME]"
        assert reviews[1].author == "[NAME]"

    @pytest.mark.asyncio
    async def test_ingest_reviews_partial_failure(
        self, settings: Settings, registry: ProductRegistry, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test graceful degradation when one store fails."""
        now = datetime.now(UTC)

        async def mock_appstore_fetch(*args, **kwargs):
            raise Exception("App Store is down!")

        async def mock_playstore_fetch(*args, **kwargs):
            from src.ingestion.models import Review
            return [
                Review(
                    id="p1",
                    store=Store.PLAYSTORE,
                    product="test_app",
                    author="Bob",
                    rating=4,
                    body="It's okay.",
                    title=None,
                    date=now,
                )
            ]

        monkeypatch.setattr("src.ingestion.appstore.AppStoreIngestor.fetch_reviews", mock_appstore_fetch)
        monkeypatch.setattr("src.ingestion.playstore.PlayStoreIngestor.fetch_reviews", mock_playstore_fetch)

        window_start = now - timedelta(days=7)
        # Should not raise exception, should return Play Store review
        reviews = await ingest_reviews("test_app", window_start, settings, registry)

        assert len(reviews) == 1
        assert reviews[0].id == "p1"
