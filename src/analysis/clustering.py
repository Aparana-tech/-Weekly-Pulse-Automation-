"""
Clustering Engine.

Reduces dimensionality of embeddings using UMAP, then clusters them using HDBSCAN.
Generates `Cluster` models containing review subsets and statistics.
"""

from __future__ import annotations

import hdbscan
import numpy as np
import structlog
import umap

from src.analysis.models import Cluster
from src.config.settings import Settings
from src.ingestion.models import Review

logger = structlog.get_logger(__name__)


def cluster_reviews(
    embedded_reviews: list[tuple[Review, np.ndarray]], settings: Settings
) -> list[Cluster]:
    """
    Cluster a list of embedded reviews into meaningful themes.

    1. Check if there are enough reviews to cluster.
    2. Reduce dimensions using UMAP.
    3. Cluster using HDBSCAN.
    4. Construct Cluster objects, skipping the noise cluster (-1).
    5. Sort by size and limit to max_themes.
    """
    if not embedded_reviews:
        logger.warning("clustering_empty_input")
        return []

    # If we have very few reviews, UMAP might fail or it's not worth clustering
    if len(embedded_reviews) < settings.min_cluster_size * 2:
        logger.warning(
            "too_few_reviews_for_clustering",
            count=len(embedded_reviews),
            min_required=settings.min_cluster_size * 2,
        )
        # Just create one giant cluster
        avg = sum(r.rating for r, _ in embedded_reviews) / len(embedded_reviews)
        return [
            Cluster(
                label=0,
                member_ids=[r.id for r, _ in embedded_reviews],
                size=len(embedded_reviews),
                avg_rating=avg,
            )
        ]

    # Extract vectors
    vectors = np.array([emb for _, emb in embedded_reviews])

    # 1. Dimensionality Reduction (UMAP)
    # n_neighbors must be less than the number of samples
    n_neighbors = min(15, len(vectors) - 1)

    logger.info("running_umap", samples=len(vectors), n_neighbors=n_neighbors)
    reducer = umap.UMAP(
        n_neighbors=n_neighbors,
        n_components=5,  # Reduce to 5D for HDBSCAN
        min_dist=0.0,
        metric="cosine",
        random_state=42,  # Deterministic
    )
    reduced_vectors = reducer.fit_transform(vectors)

    # 2. Clustering (HDBSCAN)
    logger.info("running_hdbscan", min_cluster_size=settings.min_cluster_size)
    clusterer = hdbscan.HDBSCAN(
        min_cluster_size=settings.min_cluster_size,
        metric="euclidean",
        cluster_selection_method="eom",
    )
    labels = clusterer.fit_predict(reduced_vectors)

    # 3. Build Cluster Objects
    clusters_dict: dict[int, list[Review]] = {}
    noise_count = 0

    for (review, _), label in zip(embedded_reviews, labels, strict=True):
        if label == -1:
            noise_count += 1
            continue

        if label not in clusters_dict:
            clusters_dict[label] = []
        clusters_dict[label].append(review)

    logger.info(
        "clustering_complete",
        total_clusters=len(clusters_dict),
        noise_reviews=noise_count,
        clustered_reviews=len(embedded_reviews) - noise_count,
    )

    # 4. Construct Cluster models
    clusters: list[Cluster] = []
    for label, reviews in clusters_dict.items():
        avg = sum(r.rating for r in reviews) / len(reviews)
        clusters.append(
            Cluster(
                label=label,
                member_ids=[r.id for r in reviews],
                size=len(reviews),
                avg_rating=avg,
            )
        )
        
    # 5. Sort by size descending and enforce max themes
    clusters.sort(key=lambda c: c.size, reverse=True)
    
    if len(clusters) > settings.max_themes:
        logger.info(
            "truncating_clusters",
            found=len(clusters),
            limit=settings.max_themes,
        )
        clusters = clusters[:settings.max_themes]

    return clusters
