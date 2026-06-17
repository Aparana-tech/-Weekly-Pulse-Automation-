"""
Tests for Merger and Deduplicator.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from src.config.settings import Settings
from src.ingestion.merger import merge_and_deduplicate
from src.ingestion.models import Review, Store


@pytest.fixture
def settings() -> Settings:
    return Settings(max_reviews_per_product=10)


def create_mock_review(review_id: str, store: Store, date: datetime) -> Review:
    return Review(
        id=Review.generate_id(store, "app_1", review_id),
        store=store,
        product="test_app",
        rating=5,
        body="test",
        date=date,
    )


class TestMerger:
    """Test merge_and_deduplicate."""

    def test_merge_disjoint(self, settings: Settings) -> None:
        now = datetime.now(UTC)
        appstore = [
            create_mock_review("a1", Store.APPSTORE, now),
            create_mock_review("a2", Store.APPSTORE, now - timedelta(days=1)),
        ]
        playstore = [
            create_mock_review("p1", Store.PLAYSTORE, now - timedelta(days=2)),
        ]

        merged = merge_and_deduplicate(appstore, playstore, settings)

        assert len(merged) == 3
        # Ensure it's sorted by newest first
        assert merged[0].id == appstore[0].id
        assert merged[1].id == appstore[1].id
        assert merged[2].id == playstore[0].id

    def test_deduplicate_identical(self, settings: Settings) -> None:
        now = datetime.now(UTC)
        r1 = create_mock_review("a1", Store.APPSTORE, now)
        r2 = create_mock_review("a1", Store.APPSTORE, now)  # Identical ID

        merged = merge_and_deduplicate([r1, r2], [], settings)

        assert len(merged) == 1

    def test_max_reviews_limit(self, settings: Settings) -> None:
        now = datetime.now(UTC)

        # Create 15 reviews
        appstore = [
            create_mock_review(f"a{i}", Store.APPSTORE, now - timedelta(hours=i))
            for i in range(15)
        ]

        merged = merge_and_deduplicate(appstore, [], settings)

        assert len(merged) == 10  # Settings max is 10
        # Check sorting is maintained (newest first)
        assert merged[0].date > merged[-1].date
