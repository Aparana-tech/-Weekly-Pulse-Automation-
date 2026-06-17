"""
Tests for state data models (RunRecord, RunStatus, and sub-models).
"""

from __future__ import annotations

from datetime import datetime

from src.state.models import (
    DocDelivery,
    EmailDelivery,
    LLMTokens,
    ReviewCounts,
    RunRecord,
    RunStatus,
)


class TestRunStatus:
    """Test RunStatus enum."""

    def test_values(self) -> None:
        assert RunStatus.RUNNING.value == "running"
        assert RunStatus.COMPLETED.value == "completed"
        assert RunStatus.FAILED.value == "failed"
        assert RunStatus.PARTIAL.value == "partial"


class TestLLMTokens:
    """Test LLMTokens model."""

    def test_total(self) -> None:
        t = LLMTokens(input=5000, output=1000)
        assert t.total == 6000

    def test_defaults(self) -> None:
        t = LLMTokens()
        assert t.input == 0
        assert t.output == 0
        assert t.total == 0


class TestRunRecord:
    """Test RunRecord model."""

    def _make_record(self, **overrides: object) -> RunRecord:
        defaults = {
            "run_id": "test-run-001",
            "product": "groww",
            "iso_year": 2026,
            "iso_week": 23,
        }
        defaults.update(overrides)
        return RunRecord(**defaults)  # type: ignore[arg-type]

    def test_create_record(self) -> None:
        r = self._make_record()
        assert r.run_id == "test-run-001"
        assert r.product == "groww"
        assert r.status == RunStatus.RUNNING

    def test_idempotency_key(self) -> None:
        r = self._make_record()
        assert r.idempotency_key == "groww:2026:W23"

    def test_idempotency_key_padded(self) -> None:
        r = self._make_record(iso_week=3)
        assert r.idempotency_key == "groww:2026:W03"

    def test_is_complete(self) -> None:
        r = self._make_record(status=RunStatus.COMPLETED)
        assert r.is_complete is True
        assert r.is_partial is False

    def test_is_partial(self) -> None:
        r = self._make_record(status=RunStatus.PARTIAL)
        assert r.is_partial is True
        assert r.is_complete is False

    def test_doc_not_delivered_by_default(self) -> None:
        r = self._make_record()
        assert r.doc_delivered is False

    def test_doc_delivered_when_heading_id_set(self) -> None:
        r = self._make_record()
        r.doc_delivery.heading_id = "h.abc123"
        assert r.doc_delivered is True

    def test_email_not_delivered_by_default(self) -> None:
        r = self._make_record()
        assert r.email_delivered is False

    def test_email_delivered_when_draft_id_set(self) -> None:
        r = self._make_record()
        r.email_delivery.draft_id = "draft_001"
        assert r.email_delivered is True

    def test_email_delivered_when_message_id_set(self) -> None:
        r = self._make_record()
        r.email_delivery.message_id = "msg_001"
        assert r.email_delivered is True

    def test_serialization_roundtrip(self) -> None:
        r = self._make_record(
            status=RunStatus.COMPLETED,
            reviews_fetched=ReviewCounts(appstore=100, playstore=200, total=300),
            llm_tokens=LLMTokens(input=5000, output=1000, estimated_cost_usd=0.15),
        )
        r.doc_delivery = DocDelivery(
            document_id="doc_123",
            heading_id="h.abc",
            section_anchor="groww-2026-W23",
            delivered_at=datetime(2026, 6, 9, 6, 30),
        )
        r.email_delivery = EmailDelivery(
            draft_id="d_001",
            message_id="m_001",
            recipients=["team@example.com"],
            mode="sent",
            delivered_at=datetime(2026, 6, 9, 6, 31),
        )

        data = r.model_dump()
        r2 = RunRecord(**data)
        assert r2.idempotency_key == "groww:2026:W23"
        assert r2.reviews_fetched.total == 300
        assert r2.doc_delivery.heading_id == "h.abc"
        assert r2.email_delivery.message_id == "m_001"
        assert r2.llm_tokens.total == 6000

    def test_started_at_auto(self) -> None:
        r = self._make_record()
        assert r.started_at is not None
