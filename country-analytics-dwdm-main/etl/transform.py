"""
ETL Transform Module for Country Analytics.

Performs data cleaning, schema validation, field normalization,
type conversions, derived metric calculation, and deduplication.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Tuple

logger = logging.getLogger("country_analytics.transform")


def _safe_str(val: Any, default: str | None = None) -> str | None:
    if val is None:
        return default
    s = str(val).strip()
    return s if s else default


def _safe_int(val: Any, default: int = 0) -> int:
    if val is None:
        return default
    try:
        # Handles numeric strings, floats, ints
        return max(0, int(float(val)))
    except (ValueError, TypeError):
        return default


def _safe_float(val: Any, default: float | None = None) -> float | None:
    if val is None:
        return default
    try:
        f = float(val)
        return max(0.0, f) if f >= 0 else default
    except (ValueError, TypeError):
        return default


def _safe_bool_int(val: Any, default: int = 0) -> int:
    if val is None:
        return default
    if isinstance(val, bool):
        return 1 if val else 0
    if isinstance(val, (int, float)):
        return 1 if val > 0 else 0
    s = str(val).strip().lower()
    return 1 if s in ("true", "1", "yes", "t") else 0


def transform_countries(raw_records: list[dict[str, Any]]) -> Tuple[list[dict[str, Any]], dict[str, int]]:
    """
    Transforms raw country records into clean, validated records.

    Returns:
        tuple of (transformed_records_list, transformation_metrics)
    """
    cleaned: list[dict[str, Any]] = []
    seen_cca3: set[str] = set()
    metrics = {
        "raw_count": len(raw_records),
        "valid_count": 0,
        "duplicate_count": 0,
        "invalid_count": 0,
    }

    for idx, item in enumerate(raw_records):
        if not isinstance(item, dict):
            logger.warning("Record #%d is not a valid JSON dictionary; skipping", idx)
            metrics["invalid_count"] += 1
            continue

        # Extract and validate ISO alpha-3 code (cca3)
        raw_cca3 = item.get("cca3") or item.get("iso3") or item.get("alpha3Code") or item.get("code")
        if not raw_cca3 or not isinstance(raw_cca3, str):
            logger.warning("Record #%d missing ISO-3 country code; skipping", idx)
            metrics["invalid_count"] += 1
            continue

        cca3 = raw_cca3.strip().upper()
        if len(cca3) != 3:
            logger.warning("Record #%d has invalid cca3 length '%s'; skipping", idx, cca3)
            metrics["invalid_count"] += 1
            continue

        # Deduplication check
        if cca3 in seen_cca3:
            logger.warning("Duplicate record detected for cca3 '%s'; discarding redundant record", cca3)
            metrics["duplicate_count"] += 1
            continue
        seen_cca3.add(cca3)

        # Extract name
        name_obj = item.get("name")
        if isinstance(name_obj, dict):
            common_name = _safe_str(name_obj.get("common"))
            official_name = _safe_str(name_obj.get("official"))
        else:
            common_name = _safe_str(item.get("common_name") or item.get("name"))
            official_name = _safe_str(item.get("official_name") or common_name)

        if not common_name:
            common_name = f"Country-{cca3}"

        # Capital (can be list or string)
        raw_capital = item.get("capital")
        if isinstance(raw_capital, list) and len(raw_capital) > 0:
            capital = _safe_str(raw_capital[0])
        else:
            capital = _safe_str(raw_capital)

        # Region & Subregion
        region = _safe_str(item.get("region"), default="Unspecified")
        subregion = _safe_str(item.get("subregion"))

        # Numeric metrics
        population = _safe_int(item.get("population"), default=0)
        area_km2 = _safe_float(item.get("area") or item.get("area_km2"))

        # Lat/Lng
        latlng = item.get("latlng") or []
        latitude = None
        longitude = None
        if isinstance(latlng, list) and len(latlng) >= 2:
            latitude = _safe_float(latlng[0])
            longitude = _safe_float(latlng[1])

        # Booleans
        landlocked = _safe_bool_int(item.get("landlocked"), 0)
        un_member = _safe_bool_int(item.get("unMember") or item.get("un_member"), 1)
        independent = _safe_bool_int(item.get("independent"), 1)

        # Flag description / alt
        flags_obj = item.get("flags") or {}
        flag_desc = flags_obj.get("alt") if isinstance(flags_obj, dict) else _safe_str(flags_obj)

        # Currencies & Languages normalized to dict / json
        currencies = item.get("currencies") or {}
        if not isinstance(currencies, dict):
            currencies = {}

        languages = item.get("languages") or {}
        if not isinstance(languages, dict):
            languages = {}

        # Derived metric: population density
        pop_density = None
        if area_km2 and area_km2 > 0:
            pop_density = round(population / area_km2, 4)

        record = {
            "cca3": cca3,
            "common_name": common_name,
            "official_name": official_name,
            "capital": capital,
            "region": region,
            "subregion": subregion,
            "area_km2": area_km2,
            "population": population,
            "population_density": pop_density,
            "latitude": latitude,
            "longitude": longitude,
            "landlocked": landlocked,
            "un_member": un_member,
            "independent": independent,
            "flag_description": flag_desc,
            "currencies_json": json.dumps(currencies),
            "languages_json": json.dumps(languages),
            "raw_json": json.dumps(item),
        }

        cleaned.append(record)
        metrics["valid_count"] += 1

    logger.info(
        "Transform finished: %d valid, %d duplicates removed, %d invalid skipped",
        metrics["valid_count"],
        metrics["duplicate_count"],
        metrics["invalid_count"],
    )
    return cleaned, metrics
