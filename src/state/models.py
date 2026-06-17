"""
State Data Models — Run ledger records for idempotency and audit.

Each pipeline execution creates a ``RunRecord`` that tracks:
- Pipeline status (running, completed, failed, partial)
- Ingestion metadata (review counts)
- Analysis metadata (clusters, themes, token usage)
- Delivery metadata (doc heading ID, email message/draft ID)
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class RunStatus(StrEnum):
    """Pipeline run status."""

    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


class ReviewCounts(BaseModel):
    """Review counts by source store."""

    appstore: int = Field(default=0, ge=0)
    playstore: int = Field(default=0, ge=0)
    total: int = Field(default=0, ge=0)


class ReviewWindow(BaseModel):
    """Date range of the review ingestion window."""

    start: datetime | None = None
    end: datetime | None = None


class LLMTokens(BaseModel):
    """Token usage tracking for the entire run."""

    input: int = Field(default=0, ge=0)
    output: int = Field(default=0, ge=0)
    estimated_cost_usd: float = Field(default=0.0, ge=0.0)

    @property
    def total(self) -> int:
        return self.input + self.output


class DocDelivery(BaseModel):
    """Metadata for Google Docs delivery."""

    document_id: str = Field(default="")
    heading_id: str | None = Field(
        default=None,
        description="Doc heading/element ID. None if not yet delivered.",
    )
    section_anchor: str = Field(
        default="",
        description="Stable section anchor (e.g., 'groww-2026-W23').",
    )
    delivered_at: datetime | None = Field(default=None)


class EmailDelivery(BaseModel):
    """Metadata for Gmail delivery."""

    draft_id: str | None = Field(default=None)
    message_id: str | None = Field(
        default=None,
        description="Gmail message ID. None if draft-only.",
    )
    recipients: list[str] = Field(default_factory=list)
    mode: str = Field(
        default="draft",
        description="'draft' or 'sent'.",
    )
    delivered_at: datetime | None = Field(default=None)


class RunRecord(BaseModel):
    """
    Complete record of a single pipeline execution.

    Used for:
    - Idempotency checks (has this product+week already been processed?)
    - Audit trail (what was sent, when, for which week?)
    - Partial failure recovery (resume from last successful stage)
    """

    run_id: str = Field(
        ...,
        description="UUID for this execution.",
    )
    product: str = Field(
        ...,
        description="Product slug.",
    )
    iso_year: int = Field(
        ...,
        description="ISO year.",
    )
    iso_week: int = Field(
        ...,
        ge=1,
        le=53,
        description="ISO week number.",
    )
    status: RunStatus = Field(
        default=RunStatus.RUNNING,
        description="Current pipeline status.",
    )
    started_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timestamp when the run started.",
    )
    completed_at: datetime | None = Field(
        default=None,
        description="Timestamp when the run completed.",
    )

    # Ingestion metadata
    reviews_fetched: ReviewCounts = Field(default_factory=ReviewCounts)
    review_window: ReviewWindow = Field(default_factory=ReviewWindow)

    # Analysis metadata
    clusters_found: int = Field(default=0, ge=0)
    themes_generated: int = Field(default=0, ge=0)
    quotes_proposed: int = Field(default=0, ge=0)
    quotes_validated: int = Field(default=0, ge=0)
    llm_tokens: LLMTokens = Field(default_factory=LLMTokens)

    # Delivery metadata
    doc_delivery: DocDelivery = Field(default_factory=DocDelivery)
    email_delivery: EmailDelivery = Field(default_factory=EmailDelivery)

    @property
    def idempotency_key(self) -> str:
        """Composite key for idempotency: product:year:Wweek."""
        return f"{self.product}:{self.iso_year}:W{self.iso_week:02d}"

    @property
    def is_complete(self) -> bool:
        """Whether the run completed successfully."""
        return self.status == RunStatus.COMPLETED

    @property
    def is_partial(self) -> bool:
        """Whether the run partially completed (some stages succeeded)."""
        return self.status == RunStatus.PARTIAL

    @property
    def doc_delivered(self) -> bool:
        """Whether the Google Doc section was delivered."""
        return self.doc_delivery.heading_id is not None

    @property
    def email_delivered(self) -> bool:
        """Whether the email was delivered (draft or sent)."""
        return (
            self.email_delivery.draft_id is not None
            or self.email_delivery.message_id is not None
        )
