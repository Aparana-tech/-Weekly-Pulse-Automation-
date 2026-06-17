"""
Tests for Run Ledger.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.state.models import RunRecord, RunStatus
from src.state.run_ledger import RunLedger


@pytest.fixture
def ledger_path(tmp_path: Path) -> Path:
    return tmp_path / ".pulse_ledger.json"


@pytest.fixture
def record() -> RunRecord:
    return RunRecord(
        run_id="test-123",
        product="test-product",
        iso_year=2026,
        iso_week=23,
    )


def test_ledger_initializes_empty_file(ledger_path: Path) -> None:
    ledger = RunLedger(storage_path=ledger_path)
    assert not ledger_path.exists()
    assert ledger.get_record("nonexistent") is None


def test_ledger_save_and_get(ledger_path: Path, record: RunRecord) -> None:
    ledger = RunLedger(storage_path=ledger_path)
    
    # Save the record
    ledger.save_record(record)
    
    # Check that file exists
    assert ledger_path.exists()
    
    # Get it back
    retrieved = ledger.get_record(record.idempotency_key)
    assert retrieved is not None
    assert retrieved.run_id == "test-123"
    assert retrieved.product == "test-product"
    assert retrieved.status == RunStatus.RUNNING


def test_ledger_update_record(ledger_path: Path, record: RunRecord) -> None:
    ledger = RunLedger(storage_path=ledger_path)
    ledger.save_record(record)
    
    # Update status
    record.status = RunStatus.COMPLETED
    ledger.save_record(record)
    
    # Read back from a new ledger instance to ensure persistence
    ledger2 = RunLedger(storage_path=ledger_path)
    retrieved = ledger2.get_record(record.idempotency_key)
    assert retrieved is not None
    assert retrieved.status == RunStatus.COMPLETED


def test_ledger_handles_corrupt_file(ledger_path: Path, record: RunRecord) -> None:
    # Write invalid JSON
    ledger_path.write_text("invalid json")
    
    ledger = RunLedger(storage_path=ledger_path)
    # Should not crash, should start fresh
    assert ledger.get_record(record.idempotency_key) is None
    
    # Saving a new record should overwrite the corrupt file cleanly
    ledger.save_record(record)
    assert ledger.get_record(record.idempotency_key) is not None


def test_ledger_list_runs_by_product(ledger_path: Path) -> None:
    ledger = RunLedger(storage_path=ledger_path)
    
    r1 = RunRecord(run_id="1", product="p1", iso_year=2026, iso_week=1)
    r2 = RunRecord(run_id="2", product="p1", iso_year=2026, iso_week=2)
    r3 = RunRecord(run_id="3", product="p2", iso_year=2026, iso_week=1)
    
    ledger.save_record(r1)
    ledger.save_record(r2)
    ledger.save_record(r3)
    
    p1_runs = ledger.list_runs_by_product("p1")
    assert len(p1_runs) == 2
    assert {"1", "2"} == {r.run_id for r in p1_runs}
    
    p2_runs = ledger.list_runs_by_product("p2")
    assert len(p2_runs) == 1
    assert p2_runs[0].run_id == "3"


def test_ledger_list_partial_failures(ledger_path: Path) -> None:
    ledger = RunLedger(storage_path=ledger_path)
    
    r1 = RunRecord(run_id="1", product="p1", iso_year=2026, iso_week=1)
    r1.status = RunStatus.COMPLETED
    
    r2 = RunRecord(run_id="2", product="p1", iso_year=2026, iso_week=2)
    r2.status = RunStatus.PARTIAL
    
    r3 = RunRecord(run_id="3", product="p1", iso_year=2026, iso_week=3)
    r3.status = RunStatus.FAILED
    
    r4 = RunRecord(run_id="4", product="p1", iso_year=2026, iso_week=4)
    r4.status = RunStatus.RUNNING
    
    ledger.save_record(r1)
    ledger.save_record(r2)
    ledger.save_record(r3)
    ledger.save_record(r4)
    
    failures = ledger.list_partial_failures()
    assert len(failures) == 2
    assert {"2", "3"} == {r.run_id for r in failures}
