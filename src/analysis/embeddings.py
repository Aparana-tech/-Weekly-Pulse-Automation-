"""
Embedding Engine.

Fetches embeddings for reviews using the configured embedding model (e.g., OpenAI).
Includes a local SQLite cache to avoid re-embedding the same reviews,
and tracks token usage.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import numpy as np
import structlog
import asyncio
from sentence_transformers import SentenceTransformer
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from src.config.settings import Settings
from src.ingestion.models import Review
from src.state.models import LLMTokens
from src.analysis.cost_tracker import CostTracker

logger = structlog.get_logger(__name__)


class EmbeddingEngine:
    """Generates embeddings for reviews with local caching."""

    def __init__(self, settings: Settings, cache_dir: Path | str = "data/cache"):
        self.settings = settings
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_path = self.cache_dir / "embeddings.sqlite"
        self._init_cache()

        # Initialize local SentenceTransformer model
        self.model = SentenceTransformer(self.settings.embedding_model)

    def _init_cache(self) -> None:
        """Initialize the SQLite cache table."""
        with sqlite3.connect(self.cache_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS embeddings (
                    review_id TEXT PRIMARY KEY,
                    embedding JSON NOT NULL,
                    model TEXT NOT NULL
                )
                """
            )

    def _get_cached_embedding(self, review_id: str, model: str) -> np.ndarray | None:
        """Retrieve an embedding from the cache if it exists for the same model."""
        with sqlite3.connect(self.cache_path) as conn:
            cursor = conn.execute(
                "SELECT embedding FROM embeddings WHERE review_id = ? AND model = ?",
                (review_id, model),
            )
            row = cursor.fetchone()
            if row:
                return np.array(json.loads(row[0]), dtype=np.float32)
        return None

    def _cache_embeddings(self, items: list[tuple[str, list[float]]], model: str) -> None:
        """Store multiple embeddings in the cache."""
        with sqlite3.connect(self.cache_path) as conn:
            conn.executemany(
                "INSERT OR REPLACE INTO embeddings (review_id, embedding, model) VALUES (?, ?, ?)",
                [(r_id, json.dumps(emb), model) for r_id, emb in items],
            )

    async def _fetch_embeddings_batch(
        self, texts: list[str], model: str
    ) -> tuple[list[list[float]], LLMTokens]:
        """Fetch embeddings for a batch of texts using local sentence-transformers."""
        if not texts:
            return [], LLMTokens()

        # Run the synchronous model.encode in a thread pool so we don't block the asyncio event loop
        embeddings = await asyncio.to_thread(
            self.model.encode,
            texts,
            show_progress_bar=False,
            convert_to_numpy=True
        )

        embeddings_list = embeddings.tolist()
        tokens = LLMTokens(
            input=0,  # Local embeddings don't use billable tokens
            output=0,
        )

        return embeddings_list, tokens

    def _prepare_text(self, review: Review) -> str:
        """Prepare the review text for embedding."""
        if review.title:
            return f"{review.title}\n{review.body}"
        return review.body

    async def generate_embeddings(
        self, reviews: list[Review], tracker: CostTracker
    ) -> list[tuple[Review, np.ndarray]]:
        """
        Generate embeddings for a list of reviews.
        Uses SQLite cache to skip already-embedded reviews.

        Returns:
            A List of (Review, Embedding Array)
        """
        model = self.settings.embedding_model
        batch_size = 100  # Max batch size for OpenAI API is often larger, but 100 is safe

        results: list[tuple[Review, np.ndarray]] = []
        to_embed: list[Review] = []
        to_embed_texts: list[str] = []

        # 1. Check Cache
        for review in reviews:
            cached = self._get_cached_embedding(review.id, model)
            if cached is not None:
                results.append((review, cached))
            else:
                to_embed.append(review)
                to_embed_texts.append(self._prepare_text(review))

        logger.info(
            "embedding_cache_stats",
            total=len(reviews),
            cached=len(results),
            to_fetch=len(to_embed),
            model=model,
        )

        # 2. Fetch missing embeddings in batches
        for i in range(0, len(to_embed), batch_size):
            batch_reviews = to_embed[i : i + batch_size]
            batch_texts = to_embed_texts[i : i + batch_size]

            try:
                batch_embeddings, tokens = await self._fetch_embeddings_batch(batch_texts, model)
            except Exception as e:
                logger.error("embedding_fetch_failed", error=str(e), batch_size=len(batch_texts))
                raise

            from src.analysis.cost_tracker import BudgetExceededError
            try:
                tracker.add_usage(model, tokens.input, tokens.output)
            except BudgetExceededError:
                logger.warning(
                    "token_budget_exceeded_embeddings",
                    budget=self.settings.max_tokens_per_run,
                    used=tracker.total_tokens.total,
                )
                break

            # Cache and append
            cache_items = []
            for review, emb in zip(batch_reviews, batch_embeddings, strict=True):
                arr = np.array(emb, dtype=np.float32)
                results.append((review, arr))
                cache_items.append((review.id, emb))

            self._cache_embeddings(cache_items, model)

            logger.debug("embedding_batch_processed", batch_index=i, batch_size=len(batch_reviews))

        logger.info(
            "embedding_generation_complete",
            total_embedded=len(to_embed),
        )

        return results
