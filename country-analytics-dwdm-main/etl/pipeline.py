"""
ETL Pipeline Orchestrator for Country Analytics.

Executes Extract -> Transform -> Load with structured logging,
validation checks, and execution timing.
"""

from __future__ import annotations

import logging
import sys
import time
from typing import Any

from etl.extract import extract_countries
from etl.load import load_countries
from etl.transform import transform_countries

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("country_analytics.pipeline")


def run_etl(
    api_url: str | None = None,
    use_fallback_on_error: bool = True,
) -> dict[str, Any]:
    """
    Executes the end-to-end Country Analytics ETL pipeline.

    Returns:
        dict containing comprehensive run metrics and status.
    """
    start_time = time.time()
    logger.info("=== STARTING COUNTRY ANALYTICS ETL PIPELINE ===")

    # 1. EXTRACT
    raw_data, source_type = extract_countries(
        api_url=api_url,
        use_fallback_on_error=use_fallback_on_error,
    )
    logger.info("Extract phase completed. Raw records count: %d", len(raw_data))

    # 2. TRANSFORM
    transformed_data, transform_metrics = transform_countries(raw_data)
    logger.info(
        "Transform phase completed. Valid: %d, Duplicates: %d, Invalid: %d",
        transform_metrics["valid_count"],
        transform_metrics["duplicate_count"],
        transform_metrics["invalid_count"],
    )

    if not transformed_data:
        raise ValueError("No valid records remaining after transformation!")

    # 3. LOAD
    load_summary = load_countries(
        records=transformed_data,
        source_type=source_type,
        duplicates_detected=transform_metrics["duplicate_count"],
    )

    elapsed = time.time() - start_time
    logger.info(
        "=== ETL PIPELINE COMPLETED SUCCESSFULLY in %.3f seconds (Run ID: %d, Loaded: %d) ===",
        elapsed,
        load_summary["run_id"],
        load_summary["rows_loaded"],
    )

    return {
        "status": "SUCCESS",
        "elapsed_seconds": round(elapsed, 3),
        "source_type": source_type,
        "rows_extracted": len(raw_data),
        "rows_valid": transform_metrics["valid_count"],
        "duplicates_removed": transform_metrics["duplicate_count"],
        "rows_loaded": load_summary["rows_loaded"],
        "run_id": load_summary["run_id"],
    }


if __name__ == "__main__":
    run_etl()
