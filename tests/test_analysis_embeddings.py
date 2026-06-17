"""
Tests for Embedding Engine.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from src.analysis.embeddings import EmbeddingEngine
from src.config.settings import Settings
from src.ingestion.models import Review, Store


@pytest.fixture
def settings() -> Settings:
    return Settings(embedding_model="all-MiniLM-L6-v2")


@pytest.fixture
def engine(settings: Settings, tmp_path, monkeypatch: pytest.MonkeyPatch) -> EmbeddingEngine:
    # Mock SentenceTransformer so it doesn't download the model during tests
    class MockSentenceTransformer:
        def __init__(self, model_name: str):
            pass
            
        def encode(self, texts, **kwargs):
            import numpy as np
            # Return dummy embeddings of dimension 384 (like MiniLM)
            return np.zeros((len(texts), 384), dtype=np.float32)
            
    monkeypatch.setattr("src.analysis.embeddings.SentenceTransformer", MockSentenceTransformer)
    return EmbeddingEngine(settings, cache_dir=tmp_path)


def create_mock_review(review_id: str) -> Review:
    return Review(
        id=review_id,
        store=Store.APPSTORE,
        product="test",
        rating=5,
        body="test body",
        title="test title",
        date=datetime.now(UTC),
    )


class TestEmbeddingEngine:
    def test_prepare_text(self, engine: EmbeddingEngine) -> None:
        r1 = create_mock_review("1")
        assert engine._prepare_text(r1) == "test title\ntest body"

        r2 = create_mock_review("2")
        r2.title = None
        assert engine._prepare_text(r2) == "test body"

    def test_cache_initialization(self, engine: EmbeddingEngine, tmp_path) -> None:
        db_path = tmp_path / "embeddings.sqlite"
        assert db_path.exists()

    def test_cache_read_write(self, engine: EmbeddingEngine) -> None:
        model = "test-model"
        emb = [0.1, 0.2, 0.3]

        # Write
        engine._cache_embeddings([("rev_1", emb)], model)

        # Read
        cached = engine._get_cached_embedding("rev_1", model)
        assert cached is not None
        assert list(cached) == emb

        # Read missing
        missing = engine._get_cached_embedding("rev_2", model)
        assert missing is None

        # Read wrong model
        wrong = engine._get_cached_embedding("rev_1", "other-model")
        assert wrong is None

    @pytest.mark.asyncio
    async def test_generate_embeddings_mock_api(
        self, engine: EmbeddingEngine, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        reviews = [create_mock_review("r1"), create_mock_review("r2")]

        # Mock the batch fetcher
        async def mock_fetch(texts, model):
            from src.state.models import LLMTokens
            embeddings = [[0.1, 0.2], [0.3, 0.4]]
            tokens = LLMTokens(input=10, output=0)
            return embeddings, tokens

        monkeypatch.setattr(engine, "_fetch_embeddings_batch", mock_fetch)

        # 1. First run, cache is empty
        from src.analysis.cost_tracker import CostTracker
        tracker = CostTracker(engine.settings)
        results = await engine.generate_embeddings(reviews, tracker)
        assert len(results) == 2
        assert tracker.total_tokens.input == 10

        # Check cache was populated
        assert engine._get_cached_embedding("r1", engine.settings.embedding_model) is not None

        # 2. Second run, cache should be hit
        # We can track if mock_fetch is called by wrapping it
        call_count = 0
        async def mock_fetch_again(texts, model):
            nonlocal call_count
            call_count += 1
            from src.state.models import LLMTokens
            return [], LLMTokens()

        monkeypatch.setattr(engine, "_fetch_embeddings_batch", mock_fetch_again)

        tracker2 = CostTracker(engine.settings)
        results2 = await engine.generate_embeddings(reviews, tracker2)
        assert len(results2) == 2
        assert tracker2.total_tokens.input == 0
        assert call_count == 0  # Should not have called API
