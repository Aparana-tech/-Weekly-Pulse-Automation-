"""
Tests for Idempotency module.
"""

from __future__ import annotations

import pytest

from src.state.idempotency import check_idempotency
from src.state.models import RunRecord, RunStatus


class MockRunLedger:
    def __init__(self, record: RunRecord | None = None):
        self.record = record
        
    def get_record(self, key: str) -> RunRecord | None:
        return self.record


class MockClientManager:
    def __init__(self, should_fail: bool = False):
        self.should_fail = should_fail
        
    def connect(self, server_name: str):
        class MockContext:
            async def __aenter__(self):
                return "mock_session"
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                pass
        return MockContext()


@pytest.fixture
def dummy_record() -> RunRecord:
    return RunRecord(
        run_id="123",
        product="test_app",
        iso_year=2026,
        iso_week=23,
    )


@pytest.mark.asyncio
async def test_idempotency_local_completed(dummy_record: RunRecord) -> None:
    dummy_record.status = RunStatus.COMPLETED
    ledger = MockRunLedger(dummy_record)
    manager = MockClientManager()
    
    decision, rec = await check_idempotency("test_app", 2026, 23, ledger, manager, None, "doc1") # type: ignore
    
    assert decision == "skip"
    assert rec == dummy_record


@pytest.mark.asyncio
async def test_idempotency_local_partial(dummy_record: RunRecord) -> None:
    dummy_record.status = RunStatus.PARTIAL
    ledger = MockRunLedger(dummy_record)
    manager = MockClientManager()
    
    decision, rec = await check_idempotency("test_app", 2026, 23, ledger, manager, None, "doc1") # type: ignore
    
    assert decision == "resume"
    assert rec == dummy_record


@pytest.mark.asyncio
async def test_idempotency_local_failed(dummy_record: RunRecord, monkeypatch: pytest.MonkeyPatch) -> None:
    dummy_record.status = RunStatus.FAILED
    ledger = MockRunLedger(dummy_record)
    manager = MockClientManager()
    
    # Mock remote check to return False
    async def mock_check(*args, **kwargs):
        return False
        
    monkeypatch.setattr("src.state.idempotency.check_section_exists", mock_check)
    
    decision, rec = await check_idempotency("test_app", 2026, 23, ledger, manager, None, "doc1") # type: ignore
    
    assert decision == "run"
    assert rec == dummy_record


@pytest.mark.asyncio
async def test_idempotency_remote_found(monkeypatch: pytest.MonkeyPatch) -> None:
    ledger = MockRunLedger(None) # No local record
    manager = MockClientManager()
    
    # Mock remote check to return True
    async def mock_check(*args, **kwargs):
        return True
        
    monkeypatch.setattr("src.state.idempotency.check_section_exists", mock_check)
    
    decision, rec = await check_idempotency("test_app", 2026, 23, ledger, manager, None, "doc1") # type: ignore
    
    assert decision == "skip"
    assert rec is None


@pytest.mark.asyncio
async def test_idempotency_remote_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    ledger = MockRunLedger(None) # No local record
    manager = MockClientManager()
    
    # Mock remote check to return False
    async def mock_check(*args, **kwargs):
        return False
        
    monkeypatch.setattr("src.state.idempotency.check_section_exists", mock_check)
    
    decision, rec = await check_idempotency("test_app", 2026, 23, ledger, manager, None, "doc1") # type: ignore
    
    assert decision == "run"
    assert rec is None
