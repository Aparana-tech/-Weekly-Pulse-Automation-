"""
Run Ledger.

Provides persistent storage for RunRecords using a JSON file backend.
Supports atomic writes and concurrent access protection via file locking.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Any

# Optional: use filelock if available to prevent concurrent write issues
try:
    from filelock import FileLock
    HAS_FILELOCK = True
except ImportError:
    HAS_FILELOCK = False

from src.state.models import RunRecord

logger = logging.getLogger(__name__)


class RunLedger:
    """Persistent storage for pipeline RunRecords."""

    def __init__(self, storage_path: str | Path = ".pulse_ledger.json"):
        self.storage_path = Path(storage_path)
        self.lock_path = self.storage_path.with_suffix(".lock")
        self._cache: dict[str, RunRecord] = {}
        
        # Ensure parent directory exists
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initial load
        self._load()

    def _get_lock(self) -> Any:
        """Get a file lock if filelock package is available, else a dummy lock."""
        if HAS_FILELOCK:
            return FileLock(str(self.lock_path))
        
        # Dummy lock context manager if filelock is not installed
        class DummyLock:
            def __enter__(self) -> None: pass
            def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None: pass
        return DummyLock()

    def _load(self) -> None:
        """Load records from the JSON file into the cache."""
        if not self.storage_path.exists():
            self._cache = {}
            return

        with self._get_lock():
            try:
                with open(self.storage_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    
                self._cache = {}
                for record_dict in data:
                    record = RunRecord.model_validate(record_dict)
                    # Index by idempotency_key for fast lookups
                    self._cache[record.idempotency_key] = record
            except json.JSONDecodeError:
                logger.error(f"Ledger file {self.storage_path} is corrupted. Starting fresh.")
                self._cache = {}
            except Exception as e:
                logger.error(f"Failed to load ledger from {self.storage_path}: {e}")
                self._cache = {}

    def _save(self) -> None:
        """Save the cache to the JSON file using an atomic write."""
        with self._get_lock():
            data = [record.model_dump(mode="json") for record in self._cache.values()]
            
            # Atomic write pattern: write to temp file, then rename
            fd, temp_path = tempfile.mkstemp(
                dir=self.storage_path.parent,
                prefix=".pulse_ledger_",
                suffix=".json.tmp",
                text=True
            )
            
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)
                    
                # Atomic replace
                os.replace(temp_path, self.storage_path)
            except Exception as e:
                logger.error(f"Failed to save ledger: {e}")
                # Cleanup temp file on failure
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                raise

    def get_record(self, idempotency_key: str) -> RunRecord | None:
        """
        Get a RunRecord by its idempotency key.
        Returns None if not found.
        """
        # Always reload before reading to catch external updates
        self._load()
        return self._cache.get(idempotency_key)

    def get_run_by_key(self, product_slug: str, iso_year: int, iso_week: int) -> RunRecord | None:
        """
        Get a RunRecord by its product, year, and week.
        """
        # The key format is defined in RunRecord.idempotency_key
        key = f"{product_slug}:{iso_year}:W{iso_week:02d}"
        return self.get_record(key)

    def list_runs_by_product(self, product_slug: str, limit: int | None = None) -> list[RunRecord]:
        """List all RunRecords for a specific product, optionally limited."""
        self._load()
        runs = [r for r in self._cache.values() if r.product == product_slug]
        # Sort newest first based on started_at
        runs.sort(key=lambda r: r.started_at, reverse=True)
        return runs[:limit] if limit is not None else runs

    def list_partial_failures(self, limit: int | None = None) -> list[RunRecord]:
        """List all RunRecords that completed partially or failed, optionally limited."""
        self._load()
        from src.state.models import RunStatus
        runs = [
            r for r in self._cache.values() 
            if r.status in (RunStatus.PARTIAL, RunStatus.FAILED)
        ]
        runs.sort(key=lambda r: r.started_at, reverse=True)
        return runs[:limit] if limit is not None else runs

    def save_record(self, record: RunRecord) -> None:
        """
        Save or update a RunRecord in the ledger.
        """
        # Always reload first to merge with any concurrent changes
        self._load()
        self._cache[record.idempotency_key] = record
        self._save()
        logger.debug(f"Saved RunRecord for {record.idempotency_key} with status {record.status}")
