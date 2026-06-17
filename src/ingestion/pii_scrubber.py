"""
PII Scrubber for App Reviews.

Removes sensitive data from review bodies, titles, and author names using regex.
Matches Indian and international phone numbers, emails, Aadhaar formats,
and other potential PII patterns.
"""

from __future__ import annotations

import re

import structlog

from src.ingestion.models import Review

logger = structlog.get_logger(__name__)

# --- Regex Patterns for PII ---

EMAIL_PATTERN = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", re.IGNORECASE
)

# Indian phone (10 digits, optionally starting with +91, 91, 0, or formatted)
# Supports +91-9876543210, 09876543210, 9876543210, etc.
PHONE_PATTERN_IND = re.compile(
    r"(?<!\d)(?:\+91[\-\s]?|91[\-\s]?|0)?(?:[6-9]\d{9})(?!\d)", re.IGNORECASE
)

# International generic phone (looking for patterns that look like phone numbers)
PHONE_PATTERN_INTL = re.compile(
    r"(?<!\d)(?:\+\d{1,3}[\-\s]?)?\(?\d{2,4}\)?[\-\s]?\d{3,4}[\-\s]?\d{3,4}(?:[\-\s]?\d{3,4})?(?!\d)", re.IGNORECASE
)

# Aadhaar (12 digits, often grouped by 4 spaces/dashes). Must not follow a '+' sign (to avoid matching phone numbers).
AADHAAR_PATTERN = re.compile(
    r"(?<!\+)\b\d{4}[\-\s]?\d{4}[\-\s]?\d{4}\b", re.IGNORECASE
)

# PAN Card (5 letters, 4 digits, 1 letter)
PAN_PATTERN = re.compile(
    r"\b[A-Z]{5}[0-9]{4}[A-Z]{1}\b", re.IGNORECASE
)

# UPI ID (username@bank)
UPI_PATTERN = re.compile(
    r"\b[a-zA-Z0-9.\-_]+@[a-zA-Z0-9.\-_]+\b", re.IGNORECASE
)


class PIIScrubber:
    """Detects and replaces PII in reviews."""

    def __init__(self, use_presidio: bool = False) -> None:
        self.stats: dict[str, int] = {
            "emails_scrubbed": 0,
            "phones_scrubbed": 0,
            "ids_scrubbed": 0,
            "pan_scrubbed": 0,
            "upi_scrubbed": 0,
            "authors_anonymized": 0,
            "names_scrubbed": 0,
        }
        self.use_presidio = use_presidio
        self.analyzer = None
        self.anonymizer = None

        if self.use_presidio:
            try:
                from presidio_analyzer import AnalyzerEngine
                from presidio_anonymizer import AnonymizerEngine
                self.analyzer = AnalyzerEngine()
                self.anonymizer = AnonymizerEngine()
            except ImportError:
                logger.warning("Presidio not installed. Falling back to basic regex scrubbing. Disable use_presidio_ner to hide this warning.")
                self.use_presidio = False

    def _scrub_text(self, text: str) -> str:
        """Scrub all known PII patterns from a string."""
        if not text:
            return text

        if self.use_presidio and self.analyzer and self.anonymizer:
            from presidio_anonymizer.entities import OperatorConfig
            results = self.analyzer.analyze(text=text, entities=["PERSON"], language='en')
            if results:
                self.stats["names_scrubbed"] += len(results)
                operators = {"PERSON": OperatorConfig("replace", {"new_value": "[NAME]"})}
                text = self.anonymizer.anonymize(text=text, analyzer_results=results, operators=operators).text

        # Emails
        text, n = EMAIL_PATTERN.subn("[EMAIL]", text)
        self.stats["emails_scrubbed"] += n

        # UPI IDs
        text, n = UPI_PATTERN.subn("[UPI_ID]", text)
        self.stats["upi_scrubbed"] += n

        # Indian Phones
        text, n_ind = PHONE_PATTERN_IND.subn("[PHONE]", text)

        # Aadhaar / 12-digit IDs
        text, n = AADHAAR_PATTERN.subn("[ID]", text)
        self.stats["ids_scrubbed"] += n

        # International Phones (Run after Aadhaar so Aadhaar is not parsed as intl phone)
        text, n_intl = PHONE_PATTERN_INTL.subn("[PHONE]", text)
        self.stats["phones_scrubbed"] += (n_ind + n_intl)

        # PAN Card
        text, n = PAN_PATTERN.subn("[PAN]", text)
        self.stats["pan_scrubbed"] += n

        return text

    def scrub_review(self, review: Review) -> Review:
        """
        Scrub PII from a single review.
        Returns the modified review (mutates in place, but also returns).
        """
        # Anonymize author
        if review.author and review.author != "[NAME]":
            review.author = "[NAME]"
            self.stats["authors_anonymized"] += 1

        # Body
        review.body = self._scrub_text(review.body)

        # Title
        if review.title:
            review.title = self._scrub_text(review.title)

        return review

    def scrub_reviews(self, reviews: list[Review]) -> list[Review]:
        """Scrub PII from a list of reviews."""
        for r in reviews:
            self.scrub_review(r)

        logger.info(
            "pii_scrub_complete",
            reviews_processed=len(reviews),
            stats=self.stats,
        )
        return reviews
