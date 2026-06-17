"""
Tests for PII Scrubber.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from src.ingestion.models import Review, Store
from src.ingestion.pii_scrubber import PIIScrubber


@pytest.fixture
def scrubber() -> PIIScrubber:
    return PIIScrubber()


def create_review_with_body(body: str, title: str | None = None) -> Review:
    return Review(
        id="test_id",
        store=Store.APPSTORE,
        product="test",
        author="John Doe",
        rating=5,
        body=body,
        title=title,
        date=datetime.now(UTC),
    )


class TestPIIScrubber:
    """Test PII detection and redaction."""

    def test_email_scrubbing(self, scrubber: PIIScrubber) -> None:
        r = create_review_with_body("Contact me at user.name+test@example.co.uk please.")
        r = scrubber.scrub_review(r)
        assert "[EMAIL]" in r.body
        assert "user.name" not in r.body

    def test_indian_phone_scrubbing(self, scrubber: PIIScrubber) -> None:
        phones = [
            "+919876543210",
            "+91-9876543210",
            "+91 9876543210",
            "919876543210",
            "09876543210",
            "9876543210",
        ]
        for phone in phones:
            r = create_review_with_body(f"Call {phone} for support")
            r = scrubber.scrub_review(r)
            assert "[PHONE]" in r.body
            assert phone not in r.body

    def test_aadhaar_scrubbing(self, scrubber: PIIScrubber) -> None:
        aadhars = [
            "1234 5678 9012",
            "1234-5678-9012",
            "123456789012",
        ]
        for aid in aadhars:
            r = create_review_with_body(f"My ID is {aid}.")
            r = scrubber.scrub_review(r)
            assert "[ID]" in r.body
            assert "1234" not in r.body

    def test_pan_scrubbing(self, scrubber: PIIScrubber) -> None:
        r = create_review_with_body("PAN: ABCDE1234F")
        r = scrubber.scrub_review(r)
        assert "[PAN]" in r.body
        assert "ABCDE" not in r.body

    def test_upi_scrubbing(self, scrubber: PIIScrubber) -> None:
        r = create_review_with_body("Pay to username@okhdfcbank ok?")
        r = scrubber.scrub_review(r)
        assert "[UPI_ID]" in r.body
        assert "username" not in r.body

    def test_author_anonymization(self, scrubber: PIIScrubber) -> None:
        r = create_review_with_body("test")
        assert r.author == "John Doe"
        r = scrubber.scrub_review(r)
        assert r.author == "[NAME]"

    def test_title_scrubbing(self, scrubber: PIIScrubber) -> None:
        r = create_review_with_body("test", title="Call 9876543210")
        r = scrubber.scrub_review(r)
        assert r.title == "Call [PHONE]"

    def test_stats_tracking(self, scrubber: PIIScrubber) -> None:
        r1 = create_review_with_body("Email: a@b.com, Phone: 9876543210")
        r2 = create_review_with_body("Another email test@test.com")

        scrubber.scrub_reviews([r1, r2])

        assert scrubber.stats["emails_scrubbed"] == 2
        assert scrubber.stats["phones_scrubbed"] == 1
        assert scrubber.stats["authors_anonymized"] == 2
