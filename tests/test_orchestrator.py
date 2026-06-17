"""
Tests for Pipeline Orchestrator.
"""

from __future__ import annotations

import datetime
from unittest.mock import AsyncMock

import pytest

from src.analysis.models import PulseReport, RunStats
from src.config.product_registry import ProductConfig, ProductRegistry
from src.config.settings import Settings
from src.orchestrator import run_pulse
from src.state.models import RunRecord, RunStatus
from src.state.run_ledger import RunLedger


@pytest.mark.asyncio
async def test_run_pulse_dry_run(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    settings = Settings()
    ledger = RunLedger(tmp_path / "ledger.json")
    
    registry = ProductRegistry([])
    registry._products = {
        "test_app": ProductConfig(
            slug="test_app",
            display_name="Test App",
            appstore_id="123",
            playstore_id="com.test",
            doc_id="doc1",
            stakeholder_emails=[],
        )
    }
    
    class MockClientManager:
        pass

    manager = MockClientManager()
    
    # Mock Idempotency (always Run)
    async def mock_check_idempotency(*args, **kwargs):
        return "run", None
        
    # Mock Ingestion
    async def mock_ingest(*args, **kwargs):
        return []
        
    # Mock Analysis
    async def mock_analyze(*args, **kwargs):
        return PulseReport(
            product="test_app",
            iso_year=2026,
            iso_week=23,
            themes=[],
            stats=RunStats()
        )
        
    monkeypatch.setattr("src.orchestrator.check_idempotency", mock_check_idempotency)
    monkeypatch.setattr("src.orchestrator.ingest_reviews", mock_ingest)
    monkeypatch.setattr("src.orchestrator.analyze_reviews", mock_analyze)
    
    record = await run_pulse(
        product_slug="test_app",
        iso_year=2026,
        iso_week=23,
        settings=settings,
        registry=registry,
        ledger=ledger,
        client_manager=manager, # type: ignore
        dry_run=True,
    )
    
    assert record.status == RunStatus.COMPLETED
    assert record.product == "test_app"
    assert record.iso_year == 2026
    assert record.iso_week == 23


@pytest.mark.asyncio
async def test_run_pulse_skip(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    settings = Settings()
    ledger = RunLedger(tmp_path / "ledger.json")
    
    registry = ProductRegistry([])
    registry._products = {
        "test_app": ProductConfig(
            slug="test_app",
            display_name="Test App",
            appstore_id="123",
            playstore_id="com.test",
            doc_id="doc1",
            stakeholder_emails=[],
        )
    }
    
    manager = None
    
    existing_record = RunRecord(
        run_id="abc",
        product="test_app",
        iso_year=2026,
        iso_week=23,
        status=RunStatus.COMPLETED
    )
    
    # Mock Idempotency (always Skip)
    async def mock_check_idempotency(*args, **kwargs):
        return "skip", existing_record
        
    monkeypatch.setattr("src.orchestrator.check_idempotency", mock_check_idempotency)
    
    record = await run_pulse(
        product_slug="test_app",
        iso_year=2026,
        iso_week=23,
        settings=settings,
        registry=registry,
        ledger=ledger,
        client_manager=manager, # type: ignore
        dry_run=False,
    )
    
    # Should just return the existing record
    assert record == existing_record
