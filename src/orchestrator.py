"""
Pipeline Orchestrator.

Ties together Ingestion, Analysis, Rendering, and Delivery layers.
Handles the RunRecord state machine, idempotency checks, and error propagation.
"""

from __future__ import annotations

import json
import structlog
from datetime import UTC, datetime

from src.analysis.models import RunStats
from src.analysis.pipeline import analyze_reviews
from src.config.product_registry import ProductRegistry
from src.config.settings import Settings
from src.config.week_utils import iso_week_date_range, review_window_range
from src.delivery import deliver_pulse, MCPClientManager
from src.ingestion.models import Store
from src.ingestion.pipeline import ingest_reviews
from src.rendering import render_all
from src.state.idempotency import check_idempotency
from src.state.models import RunRecord, RunStatus
from src.state.run_ledger import RunLedger

from src.config.logging import bind_run_context, bind_stage

logger = structlog.get_logger(__name__)


async def run_pulse(
    product_slug: str,
    iso_year: int,
    iso_week: int,
    settings: Settings,
    registry: ProductRegistry,
    ledger: RunLedger,
    client_manager: MCPClientManager,
    dry_run: bool = False,
) -> RunRecord:
    """
    Execute the entire Pulse pipeline for a given product and week.
    
    1. Check Idempotency
    2. Create/Update RunRecord
    3. Ingest Reviews
    4. Analyze Reviews
    5. Render Payloads
    6. Deliver Payloads
    7. Update RunRecord
    """
    # Bind run context
    run_id = f"{product_slug}_{iso_year}_W{iso_week:02d}_{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}"
    bind_run_context(run_id, product_slug, iso_year, iso_week)
    bind_stage("init")

    logger.info("pulse_run_started", product=product_slug, iso_week=iso_week, iso_year=iso_year)
    
    # 1. Look up product
    product = registry.get_or_raise(product_slug)
    
    # 2. Check Idempotency
    decision, record = await check_idempotency(
        product_slug=product_slug,
        iso_year=iso_year,
        iso_week=iso_week,
        ledger=ledger,
        client_manager=client_manager,
        settings=settings,
        doc_id=product.doc_id,
    )
    
    if decision == "skip" and record:
        logger.info(f"Skipping run for {product_slug} (W{iso_week:02d}): already completed.")
        return record
        
    # Create new record if None, or update status if resuming
    if not record:
        import uuid
        record = RunRecord(
            run_id=str(uuid.uuid4()),
            product=product_slug,
            iso_year=iso_year,
            iso_week=iso_week,
            status=RunStatus.RUNNING,
        )
    else:
        record.status = RunStatus.RUNNING
        
    ledger.save_record(record)
    
    try:
        # Calculate date ranges
        bind_stage("ingestion")
        logger.info("ingestion_started")
        
        # Determine the date range for ingestion
        window_start, window_end = review_window_range(
            year=iso_year, week=iso_week, window_weeks=settings.review_window_weeks
        )
        record.review_window.start = datetime.combine(window_start, datetime.min.time()).replace(tzinfo=UTC)
        record.review_window.end = datetime.combine(window_end, datetime.min.time()).replace(tzinfo=UTC)
        
        # 3. Ingestion
        logger.info("Executing ingestion pipeline")
        reviews = await ingest_reviews(
            product_slug=product_slug,
            window_start=window_start,
            settings=settings,
            registry=registry,
        )
        
        # Filter to make sure we don't include reviews past week_end
        week_end_dt = datetime.combine(window_end, datetime.max.time()).replace(tzinfo=UTC)
        reviews = [r for r in reviews if r.date <= week_end_dt]
        
        # Update ingestion metadata
        record.reviews_fetched.total = len(reviews)
        record.reviews_fetched.appstore = sum(1 for r in reviews if r.store == Store.APPSTORE)
        record.reviews_fetched.playstore = sum(1 for r in reviews if r.store == Store.PLAYSTORE)
        ledger.save_record(record)
        
        # Save raw reviews to a JSON file for the user
        import json
        import os
        os.makedirs("downloads", exist_ok=True)
        reviews_dump_path = f"downloads/{product_slug}_{iso_year}_W{iso_week:02d}_reviews.json"
        with open(reviews_dump_path, "w", encoding="utf-8") as f:
            # Review objects are Pydantic models, so we can dump them easily
            json.dump([r.model_dump(mode="json") for r in reviews], f, indent=2)
        logger.info(f"Saved {len(reviews)} raw reviews to {reviews_dump_path}")
        
        # 4. Analysis
        logger.info("Executing analysis pipeline")
        bind_stage("analysis")
        logger.info("analysis_started")
        report = await analyze_reviews(reviews, settings)
        
        # Update report with correct metadata
        report.product = product_slug
        report.display_name = product.display_name
        report.iso_year = iso_year
        report.iso_week = iso_week
        report.review_window_start = datetime(window_start.year, window_start.month, window_start.day, tzinfo=UTC)
        report.review_window_end = datetime(window_end.year, window_end.month, window_end.day, tzinfo=UTC)
        
        # Update analysis metadata
        record.clusters_found = report.stats.clusters_found
        record.themes_generated = len(report.themes)
        record.quotes_validated = sum(len(t.validated_quotes) for t in report.themes)
        # Using a default LLMTokens update since analysis might have populated `report.stats`
        # Wait, report.stats doesn't directly have llm_tokens. Let's just track the fact it finished.
        ledger.save_record(record)
        
        # Save PulseReport to JSON
        report_dump_path = f"downloads/{product_slug}_{iso_year}_W{iso_week:02d}_report.json"
        with open(report_dump_path, "w", encoding="utf-8") as f:
            f.write(report.model_dump_json(indent=2))
        logger.info(f"Saved PulseReport to {report_dump_path}")

        
        # 5. Rendering
        logger.info("Rendering delivery payloads")
        bind_stage("rendering")
        logger.info("rendering_started")
        rendered = render_all(report, doc_id=product.doc_id)
        docs_payload = rendered["docs_payload"]
        email_content = rendered["email_content"]
        
        # 6. Delivery
        bind_stage("delivery")
        logger.info("delivery_started")
        if dry_run:
            logger.info("dry_run_skipping_delivery")
            record.status = RunStatus.COMPLETED
            record.completed_at = datetime.now(UTC)
            ledger.save_record(record)
            return record
            
        logger.info("Executing delivery pipeline")
        delivery_results = await deliver_pulse(
            report=report,
            docs_payload=docs_payload,
            email_content=email_content,
            doc_id=product.doc_id,
            email_recipients=product.stakeholder_emails,
            settings=settings,
            client_manager=client_manager,
        )
        
        # Process delivery results into the RunRecord
        if "Success" in delivery_results.get("docs_delivery", "") or "Skipped" in delivery_results.get("docs_delivery", ""):
            # Note: exact heading IDs aren't returned by batchUpdate easily in our implementation,
            # so we just mark the anchor as delivered.
            record.doc_delivery.document_id = product.doc_id
            record.doc_delivery.heading_id = report.section_anchor
            record.doc_delivery.section_anchor = report.section_anchor
            record.doc_delivery.delivered_at = datetime.now(UTC)
            
        email_res = delivery_results.get("email_delivery", "")
        if "Success" in email_res:
            record.email_delivery.mode = settings.email_mode
            record.email_delivery.recipients = product.stakeholder_emails
            record.email_delivery.delivered_at = datetime.now(UTC)
            
            # Very basic extraction of ID from result string
            if "ID:" in email_res:
                parts = email_res.split("ID:")
                if len(parts) > 1:
                    extracted_id = parts[1].strip(" )")
                    if settings.email_mode == "draft":
                        record.email_delivery.draft_id = extracted_id
                    else:
                        record.email_delivery.message_id = extracted_id
                        
        # Final status check
        if "Error" in delivery_results.get("docs_delivery", "") or "Error" in delivery_results.get("email_delivery", ""):
            record.status = RunStatus.PARTIAL
        else:
            record.status = RunStatus.COMPLETED
            record.completed_at = datetime.now(UTC)
            
        # Save final state
        ledger.save_record(record)
        
        bind_stage("complete")
        logger.info("pulse_run_completed", status=record.status.value)
        
        return record
        
    except Exception as e:
        logger.exception(f"Pipeline failed for {product_slug}: {e}")
        record.status = RunStatus.FAILED
        ledger.save_record(record)
        raise
