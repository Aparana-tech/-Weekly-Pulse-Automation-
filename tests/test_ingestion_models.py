"""
Tests for ingestion data models (Review, Store).
"""

from __future__ import annotations

from datetime import datetime

import pytest

from src.ingestion.models import Review, Store


class TestStore:
    """Test the Store enum."""

    def test_appstore_value(self) -> None:
        assert Store.APPSTORE.value == "appstore"

    def test_playstore_value(self) -> None:
        assert Store.PLAYSTORE.value == "playstore"

    def test_store_from_string(self) -> None:
        assert Store("appstore") == Store.APPSTORE
        assert Store("playstore") == Store.PLAYSTORE


class TestReviewIDGeneration:
    """Test deterministic review ID generation."""

    def test_generate_id_deterministic(self) -> None:
        id1 = Review.generate_id(Store.APPSTORE, "123456", "rev_001")
        id2 = Review.generate_id(Store.APPSTORE, "123456", "rev_001")
        assert id1 == id2

    def test_generate_id_differs_by_store(self) -> None:
        id1 = Review.generate_id(Store.APPSTORE, "123456", "rev_001")
        id2 = Review.generate_id(Store.PLAYSTORE, "123456", "rev_001")
        assert id1 != id2

    def test_generate_id_differs_by_review_id(self) -> None:
        id1 = Review.generate_id(Store.APPSTORE, "123456", "rev_001")
        id2 = Review.generate_id(Store.APPSTORE, "123456", "rev_002")
        assert id1 != id2

    def test_generate_id_length(self) -> None:
        rid = Review.generate_id(Store.APPSTORE, "123456", "rev_001")
        assert len(rid) == 16

    def test_generate_id_with_string_store(self) -> None:
        id1 = Review.generate_id("appstore", "123456", "rev_001")
        id2 = Review.generate_id(Store.APPSTORE, "123456", "rev_001")
        assert id1 == id2


class TestReviewModel:
    """Test Review model creation and validation."""

    def _make_review(self, **overrides: object) -> Review:
        defaults = {
            "id": "abc123def4567890",
            "store": Store.APPSTORE,
            "product": "groww",
            "author": "[NAME]",
            "rating": 4,
            "title": "Great app",
            "body": "Really love using this app for trading.",
            "date": datetime(2026, 6, 1, 12, 0, 0),
            "version": "5.2.1",
            "language": "en",
            "raw_length": 50,
        }
        defaults.update(overrides)
        return Review(**defaults)  # type: ignore[arg-type]

    def test_create_review(self) -> None:
        r = self._make_review()
        assert r.id == "abc123def4567890"
        assert r.store == Store.APPSTORE
        assert r.product == "groww"
        assert r.rating == 4

    def test_review_with_no_title(self) -> None:
        r = self._make_review(title=None)
        assert r.title is None

    def test_rating_validation_too_low(self) -> None:
        with pytest.raises(ValueError):
            self._make_review(rating=0)

    def test_rating_validation_too_high(self) -> None:
        with pytest.raises(ValueError):
            self._make_review(rating=6)

    def test_valid_ratings(self) -> None:
        for rating in range(1, 6):
            r = self._make_review(rating=rating)
            assert r.rating == rating

    def test_text_for_embedding_with_title(self) -> None:
        r = self._make_review(title="Great app", body="Works well")
        assert r.text_for_embedding == "Great app Works well"

    def test_text_for_embedding_without_title(self) -> None:
        r = self._make_review(title=None, body="Works well")
        assert r.text_for_embedding == "Works well"

    def test_serialization_roundtrip(self) -> None:
        r = self._make_review()
        data = r.model_dump()
        r2 = Review(**data)
        assert r == r2

    def test_json_roundtrip(self) -> None:
        r = self._make_review()
        json_str = r.model_dump_json()
        r2 = Review.model_validate_json(json_str)
        assert r == r2

    def test_default_language(self) -> None:
        r = self._make_review()
        assert r.language == "en"

    def test_default_raw_length(self) -> None:
        # Create without explicit raw_length
        r = Review(
            id="test",
            store=Store.APPSTORE,
            product="groww",
            rating=3,
            body="test body",
            date=datetime(2026, 1, 1),
        )
        assert r.raw_length == 0
