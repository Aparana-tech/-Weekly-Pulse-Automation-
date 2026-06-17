"""
Ingestion Data Models — Normalized review representation.

All reviews from App Store and Play Store are normalized into the ``Review``
model after ingestion and PII scrubbing.
"""

from __future__ import annotations

import hashlib
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field, field_validator


class Store(StrEnum):
    """Source store for a review."""

    APPSTORE = "appstore"
    PLAYSTORE = "playstore"


class Review(BaseModel):
    """
    Normalized app review from either App Store or Play Store.

    The ``id`` field is a deterministic hash of (store, app_id, review_id),
    ensuring stable identity across re-runs.
    """

    id: str = Field(
        ...,
        description="Deterministic hash of (store, app_id, review_id).",
    )
    store: Store = Field(
        ...,
        description="Source store: 'appstore' or 'playstore'.",
    )
    product: str = Field(
        ...,
        description="Product slug (e.g., 'groww').",
    )
    author: str = Field(
        default="",
        description="Author name (anonymized after PII scrub).",
    )
    rating: int = Field(
        ...,
        ge=1,
        le=5,
        description="Star rating (1-5).",
    )
    title: str | None = Field(
        default=None,
        description="Review title. May be None (Play Store reviews often lack titles).",
    )
    body: str = Field(
        ...,
        description="Review text (PII-scrubbed).",
    )
    date: datetime = Field(
        ...,
        description="Review submission date (ISO-8601).",
    )
    version: str | None = Field(
        default=None,
        description="App version at time of review, if available.",
    )
    language: str = Field(
        default="en",
        description="ISO 639-1 language code.",
    )
    raw_length: int = Field(
        default=0,
        ge=0,
        description="Original character count of body (pre-PII scrub).",
    )

    @field_validator("rating")
    @classmethod
    def _validate_rating(cls, v: int) -> int:
        if not 1 <= v <= 5:
            raise ValueError(f"Rating must be 1-5, got {v}")
        return v

    @staticmethod
    def generate_id(store: Store | str, app_id: str, review_id: str) -> str:
        """
        Generate a deterministic review ID from its components.

        Parameters
        ----------
        store
            Source store.
        app_id
            App Store numeric ID or Play Store package name.
        review_id
            Store-specific review identifier.

        Returns
        -------
        str
            SHA-256 hex digest (first 16 chars).
        """
        store_val = store.value if isinstance(store, Store) else store
        raw = f"{store_val}:{app_id}:{review_id}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    @property
    def text_for_embedding(self) -> str:
        """Concatenated text used for generating embeddings."""
        parts = []
        if self.title:
            parts.append(self.title)
        parts.append(self.body)
        return " ".join(parts)
