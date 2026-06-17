"""
Integration test for Analysis Pipeline.
"""

from __future__ import annotations

from datetime import UTC, datetime

import numpy as np
import pytest

from src.analysis.pipeline import analyze_reviews
from src.config.settings import Settings
from src.ingestion.models import Review, Store


@pytest.fixture
def settings() -> Settings:
    return Settings(
        min_cluster_size=2,
        max_themes_per_run=2,
    )


def create_mock_review(review_id: str, body: str) -> Review:
    return Review(
        id=review_id,
        store=Store.APPSTORE,
        product="test_app",
        rating=5,
        body=body,
        date=datetime.now(UTC),
    )


class TestAnalysisPipeline:
    @pytest.mark.asyncio
    async def test_analyze_reviews_empty(self, settings: Settings) -> None:
        report = await analyze_reviews([], settings)
        assert report.product == "unknown"
        assert report.themes == []
        assert report.stats.total_reviews == 0

    @pytest.mark.asyncio
    async def test_analyze_reviews_success(
        self, settings: Settings, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        reviews = [
            create_mock_review("1", "App crashes on login!"),
            create_mock_review("2", "Crashes immediately after login."),
            create_mock_review("3", "Love the new UI design."),
            create_mock_review("4", "The UI is so beautiful now."),
        ]

        # Mock Embeddings
        async def mock_generate_embeddings(self_obj, revs, tracker):
            emb_crash = np.zeros(10)
            emb_crash[0] = 1.0

            emb_ui = np.zeros(10)
            emb_ui[1] = 1.0

            results = []
            for r in revs:
                if "crash" in r.body.lower():
                    results.append((r, emb_crash))
                else:
                    results.append((r, emb_ui))

            tracker.add_usage("text-embedding-3-small", 40, 0)
            return results

        monkeypatch.setattr("src.analysis.embeddings.EmbeddingEngine.generate_embeddings", mock_generate_embeddings)

        # Mock Clustering (UMAP/HDBSCAN is too complex to mock reliably while maintaining tests,
        # but wait, the cluster_reviews function is isolated. Let's mock it directly.)
        def mock_cluster_reviews(embedded, settings):
            from src.analysis.models import Cluster
            c1 = Cluster(label=1, member_ids=["1", "2"], size=2, avg_rating=5.0)
            c2 = Cluster(label=2, member_ids=["3", "4"], size=2, avg_rating=5.0)
            return [c1, c2]

        monkeypatch.setattr("src.analysis.pipeline.cluster_reviews", mock_cluster_reviews)

        # Mock LLM Summarization
        async def mock_summarize_all(self_obj, clusters, reviews_map, tracker):
            from src.analysis.models import Quote, Theme

            themes = [
                Theme(
                    name="Crashes",
                    description="App crashes on login",
                    quotes=[Quote(text="crashes on login!", review_id="1", rating=5, store="appstore", date=datetime.now(UTC))],
                    actions=[],
                    review_count=2,
                ),
                Theme(
                    name="UI Design",
                    description="Users like the UI",
                    quotes=[Quote(text="UI is so beautiful", review_id="4", rating=5, store="appstore", date=datetime.now(UTC))],
                    actions=[],
                    review_count=2,
                )
            ]
            tracker.add_usage("gpt-4o-mini", 200, 100)
            return themes

        monkeypatch.setattr("src.analysis.summarizer.LLMSummarizer.summarize_all", mock_summarize_all)

        # Execute
        report = await analyze_reviews(reviews, settings)

        assert report.product == "test_app"
        assert len(report.themes) == 2

        # Check Quote Validation
        assert report.themes[0].quotes[0].validated is True
        assert report.themes[1].quotes[0].validated is True

        # Check stats
        assert report.stats.total_reviews == 4
        assert report.stats.clusters_found == 2
        assert report.stats.quotes_proposed == 2
        assert report.stats.quotes_validated == 2
        assert report.stats.llm_usage.total_tokens == 340
