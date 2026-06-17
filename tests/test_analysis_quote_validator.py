"""
Tests for Quote Validator.
"""

from __future__ import annotations

from datetime import UTC, datetime

from src.analysis.models import Quote, Theme
from src.analysis.quote_validator import validate_quotes
from src.ingestion.models import Review, Store


def create_mock_review(body: str) -> Review:
    return Review(
        id="1",
        store=Store.APPSTORE,
        product="test",
        rating=5,
        body=body,
        date=datetime.now(UTC),
    )


class TestQuoteValidator:
    def test_all_valid(self) -> None:
        reviews = [
            create_mock_review("This is a great app."),
            create_mock_review("I love the new design!"),
        ]
        dummy_date = datetime.now(UTC)
        theme = Theme(
            name="Positive",
            description="Good things",
            quotes=[
                Quote(text="great app", review_id="1", rating=5, store="appstore", date=dummy_date),
                Quote(text="new design!", review_id="2", rating=5, store="appstore", date=dummy_date),
            ],
            actions=[],
            review_count=2,
        )

        result = validate_quotes(theme, reviews)
        assert len(result.quotes) == 2
        assert result.quotes[0].validated is True
        assert result.quotes[1].validated is True

    def test_some_invalid(self) -> None:
        reviews = [
            create_mock_review("This is a great app."),
        ]
        dummy_date = datetime.now(UTC)
        theme = Theme(
            name="Positive",
            description="Good things",
            quotes=[
                Quote(text="great app", review_id="1", rating=5, store="appstore", date=dummy_date),  # Valid
                Quote(text="awesome app", review_id="1", rating=5, store="appstore", date=dummy_date),  # Invalid (hallucinated)
            ],
            actions=[],
            review_count=1,
        )

        result = validate_quotes(theme, reviews)
        assert len(result.quotes) == 1
        assert result.quotes[0].text == "great app"
        assert result.quotes[0].validated is True

    def test_all_invalid(self) -> None:
        reviews = [
            create_mock_review("This is a great app."),
        ]
        dummy_date = datetime.now(UTC)
        theme = Theme(
            name="Positive",
            description="Good things",
            quotes=[
                Quote(text="terrible app", review_id="1", rating=5, store="appstore", date=dummy_date),
            ],
            actions=[],
            review_count=1,
        )

        result = validate_quotes(theme, reviews)
        assert len(result.quotes) == 0
