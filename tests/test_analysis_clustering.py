"""
Tests for Clustering Engine.
"""

from __future__ import annotations

from datetime import UTC, datetime

import numpy as np

from src.analysis.clustering import cluster_reviews
from src.config.settings import Settings
from src.ingestion.models import Review, Store


def create_mock_review(review_id: str) -> Review:
    return Review(
        id=review_id,
        store=Store.APPSTORE,
        product="test",
        rating=5,
        body="test",
        date=datetime.now(UTC),
    )


class TestClusteringEngine:
    def test_clustering_empty(self) -> None:
        settings = Settings()
        clusters = cluster_reviews([], settings)
        assert clusters == []

    def test_clustering_too_few_reviews(self) -> None:
        # If there are fewer than min_cluster_size * 2, it should fallback to 1 giant cluster
        settings = Settings(min_cluster_size=5)
        # Create 8 reviews (less than 10)
        embedded_reviews = [
            (create_mock_review(str(i)), np.random.rand(1536))
            for i in range(8)
        ]

        clusters = cluster_reviews(embedded_reviews, settings)
        assert len(clusters) == 1
        assert clusters[0].size == 8

    def test_clustering_success(self) -> None:
        settings = Settings(min_cluster_size=5)

        # Create 50 synthetic embeddings
        # Make two distinct groups of vectors so HDBSCAN definitely finds 2 clusters
        np.random.seed(42)
        group1 = np.random.normal(loc=0.0, scale=0.1, size=(25, 1536))
        group2 = np.random.normal(loc=10.0, scale=0.1, size=(25, 1536))
        all_vectors = np.vstack((group1, group2))

        embedded_reviews = [
            (create_mock_review(str(i)), all_vectors[i])
            for i in range(50)
        ]

        clusters = cluster_reviews(embedded_reviews, settings)

        # Should find at least 1 cluster, probably 2
        assert len(clusters) > 0

        # Total size of all clusters + noise should be <= 50
        total_clustered = sum(c.size for c in clusters)
        assert total_clustered <= 50

        # Check sorting
        if len(clusters) > 1:
            assert clusters[0].size >= clusters[1].size
