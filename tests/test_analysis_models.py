"""
Tests for analysis data models (Theme, Quote, ActionIdea, Cluster, PulseReport, RunStats).
"""

from __future__ import annotations

from datetime import datetime

from src.analysis.models import (
    ActionIdea,
    Cluster,
    PulseReport,
    Quote,
    RunStats,
    Theme,
    TokenUsage,
)


class TestQuote:
    """Test Quote model."""

    def _make_quote(self, **overrides: object) -> Quote:
        defaults = {
            "text": "The app freezes exactly when the market opens.",
            "review_id": "abc123",
            "rating": 2,
            "store": "appstore",
            "date": datetime(2026, 5, 15),
            "validated": True,
        }
        defaults.update(overrides)
        return Quote(**defaults)  # type: ignore[arg-type]

    def test_create_quote(self) -> None:
        q = self._make_quote()
        assert q.text == "The app freezes exactly when the market opens."
        assert q.validated is True

    def test_unvalidated_quote(self) -> None:
        q = self._make_quote(validated=False)
        assert q.validated is False

    def test_default_validated_is_false(self) -> None:
        q = Quote(
            text="test",
            review_id="r1",
            rating=3,
            store="playstore",
            date=datetime(2026, 1, 1),
        )
        assert q.validated is False


class TestActionIdea:
    """Test ActionIdea model."""

    def test_create_action(self) -> None:
        a = ActionIdea(
            title="Stabilize Peak-Time Performance",
            details="Scale infra during market hours.",
            related_theme="App Performance & Bugs",
        )
        assert a.title == "Stabilize Peak-Time Performance"
        assert a.related_theme == "App Performance & Bugs"


class TestTheme:
    """Test Theme model."""

    def _make_theme(self) -> Theme:
        return Theme(
            name="App Performance & Bugs",
            description="Lag, crashes during trading hours.",
            quotes=[
                Quote(
                    text="Freezes at market open.",
                    review_id="r1",
                    rating=2,
                    store="appstore",
                    date=datetime(2026, 5, 1),
                    validated=True,
                ),
                Quote(
                    text="Hallucinated quote.",
                    review_id="r2",
                    rating=1,
                    store="playstore",
                    date=datetime(2026, 5, 2),
                    validated=False,
                ),
            ],
            actions=[
                ActionIdea(
                    title="Scale infra",
                    details="During market hours.",
                    related_theme="App Performance & Bugs",
                ),
            ],
            review_count=42,
            cluster_label=0,
        )

    def test_create_theme(self) -> None:
        t = self._make_theme()
        assert t.name == "App Performance & Bugs"
        assert t.review_count == 42
        assert len(t.quotes) == 2
        assert len(t.actions) == 1

    def test_validated_quotes_filters(self) -> None:
        t = self._make_theme()
        vq = t.validated_quotes
        assert len(vq) == 1
        assert vq[0].text == "Freezes at market open."


class TestCluster:
    """Test Cluster model."""

    def test_normal_cluster(self) -> None:
        c = Cluster(label=0, member_ids=["r1", "r2", "r3"], size=3, avg_rating=3.5)
        assert c.is_noise is False
        assert c.size == 3

    def test_noise_cluster(self) -> None:
        c = Cluster(label=-1, member_ids=["r4"], size=1, avg_rating=2.0)
        assert c.is_noise is True


class TestTokenUsage:
    """Test TokenUsage model."""

    def test_total_tokens(self) -> None:
        t = TokenUsage(input_tokens=1000, output_tokens=500, estimated_cost_usd=0.05)
        assert t.total_tokens == 1500

    def test_defaults(self) -> None:
        t = TokenUsage()
        assert t.input_tokens == 0
        assert t.output_tokens == 0
        assert t.total_tokens == 0


class TestRunStats:
    """Test RunStats model."""

    def test_quote_validation_rate(self) -> None:
        s = RunStats(quotes_proposed=10, quotes_validated=8)
        assert s.quote_validation_rate == 0.8

    def test_quote_validation_rate_zero_proposed(self) -> None:
        s = RunStats(quotes_proposed=0, quotes_validated=0)
        assert s.quote_validation_rate == 0.0


class TestPulseReport:
    """Test PulseReport model."""

    def test_section_anchor(self) -> None:
        r = PulseReport(product="groww", iso_year=2026, iso_week=23)
        assert r.section_anchor == "groww-2026-W23"

    def test_section_anchor_padded(self) -> None:
        r = PulseReport(product="kuvera", iso_year=2026, iso_week=3)
        assert r.section_anchor == "kuvera-2026-W03"

    def test_default_themes_empty(self) -> None:
        r = PulseReport(product="groww", iso_year=2026, iso_week=23)
        assert r.themes == []

    def test_generated_at_auto(self) -> None:
        r = PulseReport(product="groww", iso_year=2026, iso_week=23)
        assert r.generated_at is not None

    def test_serialization_roundtrip(self) -> None:
        r = PulseReport(
            product="groww",
            display_name="Groww",
            iso_year=2026,
            iso_week=23,
            themes=[
                Theme(
                    name="Test Theme",
                    description="A test theme.",
                    review_count=10,
                    cluster_label=0,
                )
            ],
            stats=RunStats(total_reviews=100, clusters_found=5),
        )
        data = r.model_dump()
        r2 = PulseReport(**data)
        assert r2.product == "groww"
        assert len(r2.themes) == 1
        assert r2.stats.total_reviews == 100
