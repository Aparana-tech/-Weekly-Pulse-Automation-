"""
Analysis Data Models — Themes, quotes, action ideas, and pipeline outputs.

These models represent the structured output of the analysis pipeline:
clustering results, LLM-generated themes, validated quotes, and the
final PulseReport delivered to stakeholders.
"""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, Field


class Quote(BaseModel):
    """A verbatim quote extracted from a review and validated against source text."""

    text: str = Field(
        ...,
        description="Exact verbatim text from a review.",
    )
    review_id: str = Field(
        ...,
        description="ID of the source review containing this quote.",
    )
    rating: int = Field(
        ...,
        ge=1,
        le=5,
        description="Star rating of the source review.",
    )
    store: str = Field(
        ...,
        description="Source store ('appstore' or 'playstore').",
    )
    date: datetime = Field(
        ...,
        description="Date of the source review.",
    )
    validated: bool = Field(
        default=False,
        description="Whether this quote was validated as an exact substring of source text.",
    )


class ActionIdea(BaseModel):
    """A concrete, implementable action idea proposed for a theme."""

    title: str = Field(
        ...,
        description="Short action title (e.g., 'Stabilize Peak-Time Performance').",
    )
    details: str = Field(
        ...,
        description="Detailed description of the action.",
    )
    related_theme: str = Field(
        default="",
        description="Name of the theme this action addresses.",
    )


class Theme(BaseModel):
    """
    A topic theme discovered from clustered reviews.

    Each theme has a human-readable name, description, validated quotes,
    and proposed action ideas.
    """

    name: str = Field(
        ...,
        description="Theme name (3-5 words, e.g., 'App Performance & Bugs').",
    )
    description: str = Field(
        ...,
        description="Brief description of the theme (1-2 sentences).",
    )
    quotes: list[Quote] = Field(
        default_factory=list,
        description="Validated verbatim quotes from source reviews.",
    )
    actions: list[ActionIdea] = Field(
        default_factory=list,
        description="Proposed action ideas for this theme.",
    )
    review_count: int = Field(
        default=0,
        ge=0,
        description="Number of reviews in the cluster that produced this theme.",
    )
    cluster_label: int = Field(
        default=-1,
        description="HDBSCAN cluster label that produced this theme.",
    )

    @property
    def validated_quotes(self) -> list[Quote]:
        """Return only validated quotes."""
        return [q for q in self.quotes if q.validated]


class Cluster(BaseModel):
    """
    A group of semantically similar reviews discovered by HDBSCAN.

    Clusters are intermediate results between embedding and LLM summarization.
    """

    label: int = Field(
        ...,
        description="HDBSCAN cluster label (-1 = noise).",
    )
    member_ids: list[str] = Field(
        default_factory=list,
        description="IDs of reviews in this cluster.",
    )
    size: int = Field(
        default=0,
        ge=0,
        description="Number of reviews in this cluster.",
    )
    avg_rating: float = Field(
        default=0.0,
        description="Average star rating across cluster members.",
    )

    @property
    def is_noise(self) -> bool:
        """Whether this is the HDBSCAN noise cluster."""
        return self.label == -1


class TokenUsage(BaseModel):
    """Token usage tracking for LLM calls."""

    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    estimated_cost_usd: float = Field(default=0.0, ge=0.0)

    @property
    def total_tokens(self) -> int:
        """Total input + output tokens."""
        return self.input_tokens + self.output_tokens


class RunStats(BaseModel):
    """Statistics collected during a pipeline run."""

    total_reviews: int = Field(default=0, ge=0)
    appstore_reviews: int = Field(default=0, ge=0)
    playstore_reviews: int = Field(default=0, ge=0)
    clusters_found: int = Field(default=0, ge=0)
    noise_reviews: int = Field(default=0, ge=0)
    themes_generated: int = Field(default=0, ge=0)
    quotes_proposed: int = Field(default=0, ge=0)
    quotes_validated: int = Field(default=0, ge=0)
    llm_usage: TokenUsage = Field(default_factory=TokenUsage)

    @property
    def quote_validation_rate(self) -> float:
        """Percentage of proposed quotes that passed validation."""
        if self.quotes_proposed == 0:
            return 0.0
        return self.quotes_validated / self.quotes_proposed


class PulseReport(BaseModel):
    """
    The final output of the analysis pipeline for a single product + week.

    This is the complete report ready for rendering and delivery.
    """

    product: str = Field(
        ...,
        description="Product slug.",
    )
    display_name: str = Field(
        default="",
        description="Human-readable product name.",
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
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timestamp when the report was generated.",
    )
    review_window_start: datetime | None = Field(
        default=None,
        description="Start of the review ingestion window.",
    )
    review_window_end: datetime | None = Field(
        default=None,
        description="End of the review ingestion window.",
    )
    themes: list[Theme] = Field(
        default_factory=list,
        description="Themes discovered and summarized from reviews.",
    )
    stats: RunStats = Field(
        default_factory=RunStats,
        description="Pipeline run statistics.",
    )

    @property
    def section_anchor(self) -> str:
        """Stable section anchor ID for Google Docs (e.g., 'groww-2026-W23')."""
        return f"{self.product}-{self.iso_year}-W{self.iso_week:02d}"
