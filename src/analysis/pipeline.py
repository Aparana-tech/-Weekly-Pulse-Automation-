"""
Analysis Pipeline Integration.

Wires together Embedding, Clustering, LLM Summarization, and Quote Validation.
"""

from __future__ import annotations

import structlog

from src.analysis.clustering import cluster_reviews
from src.analysis.embeddings import EmbeddingEngine
from src.analysis.cost_tracker import CostTracker
from src.analysis.models import PulseReport, RunStats, Theme, TokenUsage
from src.analysis.quote_validator import validate_quotes
from src.analysis.summarizer import LLMSummarizer
from src.config.settings import Settings
from src.ingestion.models import Review

logger = structlog.get_logger(__name__)


async def analyze_reviews(reviews: list[Review], settings: Settings) -> PulseReport:
    """
    Execute the full analysis pipeline on a list of reviews.

    1. Embed reviews
    2. Cluster embeddings
    3. Summarize clusters with LLM
    4. Validate quotes
    5. Construct final PulseReport
    """
    logger.info("analysis_pipeline_started", total_reviews=len(reviews))

    if not reviews:
        logger.warning("analysis_pipeline_empty_input")
        return PulseReport(
            product="unknown",
            iso_year=2026,
            iso_week=1,
            themes=[],
            stats=RunStats()
        )

    product_slug = reviews[0].product
    reviews_map = {r.id: r for r in reviews}

    # 0. Initialize Cost Tracker
    tracker = CostTracker(settings)

    # 1. Embeddings
    embedding_engine = EmbeddingEngine(settings)
    embedded_reviews = await embedding_engine.generate_embeddings(reviews, tracker)

    # 2. Clustering
    clusters = cluster_reviews(embedded_reviews, settings)

    # 3. LLM Summarization
    summarizer = LLMSummarizer(settings)
    raw_themes = await summarizer.summarize_all(clusters, reviews_map, tracker)

    # 4. Quote Validation
    valid_themes: list[Theme] = []
    quotes_proposed = 0
    quotes_validated = 0

    for i, theme in enumerate(raw_themes):
        # We need the original reviews for this cluster to validate quotes
        cluster_reviews_list = [reviews_map[rid] for rid in clusters[i].member_ids]

        # Track proposed count before validation filters them
        quotes_proposed += len(theme.quotes)

        # Validate
        validated_theme = validate_quotes(theme, cluster_reviews_list)

        quotes_validated += len(validated_theme.quotes)
        valid_themes.append(validated_theme)

    # Sort themes by cluster size descending (already mostly sorted by clustering, but good to ensure)
    valid_themes.sort(key=lambda t: t.review_count, reverse=True)

    # Calculate stats
    tracker.log_summary()
    totals = tracker.get_totals()
    
    stats = RunStats(
        total_reviews=len(reviews),
        appstore_reviews=sum(1 for r in reviews if r.store.value == "appstore"),
        playstore_reviews=sum(1 for r in reviews if r.store.value == "playstore"),
        clusters_found=len(clusters),
        themes_generated=len(valid_themes),
        quotes_proposed=quotes_proposed,
        quotes_validated=quotes_validated,
        llm_usage=TokenUsage(
            input_tokens=totals.input,
            output_tokens=totals.output,
            estimated_cost_usd=totals.estimated_cost_usd
        ),
    )

    logger.info(
        "analysis_pipeline_completed",
        product=product_slug,
        themes=len(valid_themes),
        tokens=stats.llm_usage.total_tokens,
        cost_usd=stats.llm_usage.estimated_cost_usd
    )

    return PulseReport(
        product=product_slug,
        iso_year=2026,  # Caller should update
        iso_week=1,  # Caller should update
        themes=valid_themes,
        stats=stats
    )
