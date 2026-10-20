"""
ETL Extract Module for Country Analytics.

Downloads country data from a configured public API endpoint or seamlessly
falls back to the verified local dataset when the network or API is unavailable.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Tuple

import requests

logger = logging.getLogger("country_analytics.extract")

# Base directory paths
BASE_DIR = Path(__file__).resolve().parent.parent
FALLBACK_FILE = BASE_DIR / "data" / "countries_fallback.json"
CACHE_FILE = BASE_DIR / "data" / "countries_raw.json"


def extract_countries(
    api_url: str | None = None,
    use_fallback_on_error: bool = True,
    timeout: int = 10,
) -> Tuple[list[dict[str, Any]], str]:
    """
    Extract country records from API or local fallback.

    Returns:
        tuple of (raw_records_list, source_type_description)
    """
    records: list[dict[str, Any]] = []
    source_type = "UNKNOWN"

    if api_url:
        logger.info("Attempting extraction from API: %s", api_url)
        try:
            response = requests.get(api_url, timeout=timeout)
            response.raise_for_status()
            payload = response.json()

            if isinstance(payload, list) and len(payload) > 0:
                records = payload
                source_type = f"API ({api_url})"
                logger.info("Successfully fetched %d records from API", len(records))
                # Cache raw response
                try:
                    CACHE_FILE.write_text(json.dumps(records, indent=2), encoding="utf-8")
                except Exception as cache_err:
                    logger.warning("Failed to cache raw response: %s", cache_err)
                return records, source_type
            else:
                logger.warning("API returned unexpected format or empty list: %s", type(payload))
        except Exception as exc:
            logger.warning("API extraction failed: %s", exc)
            if not use_fallback_on_error:
                raise

    # Fallback to local verified dataset
    logger.info("Loading records from local fallback: %s", FALLBACK_FILE)
    if not FALLBACK_FILE.exists():
        raise FileNotFoundError(f"Local fallback dataset not found at {FALLBACK_FILE}")

    try:
        raw_text = FALLBACK_FILE.read_text(encoding="utf-8")
        records = json.loads(raw_text)
        if not isinstance(records, list):
            raise ValueError(f"Fallback file did not contain a JSON list, got {type(records)}")
        source_type = f"LOCAL_FALLBACK ({FALLBACK_FILE.name})"
        logger.info("Extracted %d records from local fallback dataset", len(records))
    except Exception as exc:
        logger.error("Failed to read local fallback file: %s", exc)
        raise

    return records, source_type
