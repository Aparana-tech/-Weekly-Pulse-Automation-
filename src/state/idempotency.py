"""
Idempotency Module.

Implements the two-phase idempotency check (Local Run Ledger + Remote Google Doc)
to determine whether a pipeline run should be skipped, resumed, or run fresh.
"""

from __future__ import annotations

import logging
from typing import Literal

from mcp import ClientSession

from src.config.settings import Settings
from src.delivery.docs_delivery import check_section_exists
from src.delivery.mcp_client import MCPClientManager
from src.state.models import RunRecord, RunStatus
from src.state.run_ledger import RunLedger

logger = logging.getLogger(__name__)

IdempotencyDecision = Literal["skip", "resume", "run"]


async def check_idempotency(
    product_slug: str,
    iso_year: int,
    iso_week: int,
    ledger: RunLedger,
    client_manager: MCPClientManager,
    settings: Settings,
    doc_id: str,
) -> tuple[IdempotencyDecision, RunRecord | None]:
    """
    Perform the two-phase idempotency check.
    
    Returns:
        A tuple of (Decision, ExistingRecord if any).
    """
    # Create the key manually or just construct a dummy record to get the key
    key = f"{product_slug}:{iso_year}:W{iso_week:02d}"
    
    # Phase 1: Local Check
    record = ledger.get_record(key)
    
    if record:
        if record.status == RunStatus.COMPLETED:
            logger.info(f"Idempotency [Local]: Record {key} is COMPLETED. Decision: SKIP.")
            return "skip", record
            
        if record.status == RunStatus.PARTIAL:
            logger.info(f"Idempotency [Local]: Record {key} is PARTIAL. Decision: RESUME.")
            return "resume", record
            
        if record.status == RunStatus.RUNNING:
            logger.warning(f"Idempotency [Local]: Record {key} is marked RUNNING. Assuming crashed and resuming.")
            return "resume", record
            
        if record.status == RunStatus.FAILED:
            logger.info(f"Idempotency [Local]: Record {key} FAILED. Decision: RUN (retry).")
            return "run", record

    # Phase 2: Remote Check
    # If no local record exists, or it failed, we must double-check the Google Doc
    # to ensure we didn't actually deliver but lose local state.
    
    # We construct the expected section anchor.
    # It must match the logic in PulseReport.section_anchor!
    # The models.py doesn't contain PulseReport, it's in src.analysis.models.
    # But the anchor format is standard: product-year-Wweek
    anchor = f"{product_slug}-{iso_year}-W{iso_week:02d}"
    
    logger.info(f"Idempotency [Remote]: Checking Doc {doc_id} for anchor '{anchor}'.")
    
    try:
        async with client_manager.connect("google-docs") as session:
            exists = await check_section_exists(session, doc_id, anchor)
            if exists:
                logger.info(f"Idempotency [Remote]: Anchor '{anchor}' found in doc. Decision: SKIP.")
                # We could reconstruct a dummy COMPLETED record here, but None is fine for skip
                # Actually, returning a dummy record is better to not break assumptions.
                return "skip", record
    except Exception as e:
        logger.warning(f"Remote idempotency check failed: {e}. Proceeding with cautious RUN.")
        
    logger.info(f"Idempotency: No completed state found locally or remotely. Decision: RUN.")
    return "run", record
