"""Helpers for collision-free experiment result filenames."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


def create_run_id() -> str:
    """Return a sortable, process-safe identifier for one experiment run."""

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    return f"{timestamp}_{uuid4().hex[:8]}"


def create_unique_result_path(
    directory: Path,
    product_id: str,
    method: str,
    keyword_digest: str,
    execution_mode: str,
) -> Path:
    """Create a unique path without touching the filesystem."""

    run_id = create_run_id()
    return directory / (
        f"{product_id}_{method}_{keyword_digest}_{execution_mode}_{run_id}.json"
    )
