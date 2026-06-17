"""
Tests for Delivery Integration.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from src.analysis.models import PulseReport
from src.config.settings import Settings
from src.delivery import deliver_pulse


@pytest.mark.asyncio
async def test_deliver_pulse_success(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = Settings()
    report = PulseReport(
        product="test_app",
        iso_year=2026,
        iso_week=23,
    )
    
    class MockClientManager:
        def connect(self, server_name):
            class MockContext:
                async def __aenter__(self):
                    return "mock_session"
                async def __aexit__(self, exc_type, exc_val, exc_tb):
                    pass
            return MockContext()

    manager = MockClientManager()
    
    mock_check = AsyncMock(return_value=False)
    mock_append = AsyncMock(return_value=True)
    mock_deliver_email = AsyncMock(return_value="draft_id_123")
    
    monkeypatch.setattr("src.delivery.check_section_exists", mock_check)
    monkeypatch.setattr("src.delivery.append_section_to_doc", mock_append)
    monkeypatch.setattr("src.delivery.deliver_email", mock_deliver_email)
    
    results = await deliver_pulse(
        report=report,
        docs_payload=[],
        email_content={"subject": "S", "html_body": "B"},
        doc_id="doc_id",
        email_recipients=["test@test.com"],
        settings=settings,
        client_manager=manager, # type: ignore
    )
    
    assert results["docs_delivery"] == "Success"
    assert "Success" in results["email_delivery"]
    assert "draft_id_123" in results["email_delivery"]


@pytest.mark.asyncio
async def test_deliver_pulse_idempotent(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = Settings()
    report = PulseReport(
        product="test_app",
        iso_year=2026,
        iso_week=23,
    )
    
    class MockClientManager:
        def connect(self, server_name):
            class MockContext:
                async def __aenter__(self):
                    return "mock_session"
                async def __aexit__(self, exc_type, exc_val, exc_tb):
                    pass
            return MockContext()

    manager = MockClientManager()
    
    mock_check = AsyncMock(return_value=True)  # Returns true!
    mock_append = AsyncMock()
    mock_deliver_email = AsyncMock(return_value="draft_id_123")
    
    monkeypatch.setattr("src.delivery.check_section_exists", mock_check)
    monkeypatch.setattr("src.delivery.append_section_to_doc", mock_append)
    monkeypatch.setattr("src.delivery.deliver_email", mock_deliver_email)
    
    results = await deliver_pulse(
        report=report,
        docs_payload=[],
        email_content={"subject": "S", "html_body": "B"},
        doc_id="doc_id",
        email_recipients=["test@test.com"],
        settings=settings,
        client_manager=manager, # type: ignore
    )
    
    assert "Skipped" in results["docs_delivery"]
    assert mock_append.call_count == 0  # Should not append!
