"""
Analytics Query Engine for Country Analytics.

Executes all required analytical metrics directly against the SQLite warehouse:
1. Total number of countries
2. Total population represented
3. Population by region
4. Top 10 countries by population
5. Top 10 countries by area
6. Number of countries by region
7. Filterable country table data
8. Population density rankings & audit logs
"""

from __future__ import annotations

import json
from pathlib import Path
import sqlite3
from typing import Any

BASE_DIR = Path(__file__).resolve().parent.parent
DB_FILE = BASE_DIR / "database" / "country_analytics.db"


def _get_connection(db_path: Path = DB_FILE) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def get_country_count(db_path: Path = DB_FILE) -> int:
    """1. Total number of countries."""
    conn = _get_connection(db_path)
    try:
        row = conn.execute("SELECT COUNT(*) AS total FROM dim_country").fetchone()
        return row["total"] if row else 0
    finally:
        conn.close()


def get_total_population(db_path: Path = DB_FILE) -> int:
    """2. Total population represented in the dataset."""
    conn = _get_connection(db_path)
    try:
        row = conn.execute("SELECT COALESCE(SUM(population), 0) AS total_pop FROM fact_population").fetchone()
        return row["total_pop"] if row else 0
    finally:
        conn.close()


def get_total_area(db_path: Path = DB_FILE) -> float:
    """Total area represented in the dataset."""
    conn = _get_connection(db_path)
    try:
        row = conn.execute("SELECT COALESCE(SUM(area_km2), 0.0) AS total_area FROM dim_country").fetchone()
        return round(float(row["total_area"]), 2) if row else 0.0
    finally:
        conn.close()


def get_population_by_region(db_path: Path = DB_FILE) -> list[dict[str, Any]]:
    """3. Population by region."""
    conn = _get_connection(db_path)
    try:
        rows = conn.execute(
            """
            SELECT 
                d.region,
                COALESCE(SUM(p.population), 0) AS total_population,
                ROUND(AVG(p.population), 0) AS avg_population
            FROM dim_country d
            JOIN fact_population p ON d.country_id = p.country_id
            GROUP BY d.region
            ORDER BY total_population DESC
            """
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_top10_by_population(db_path: Path = DB_FILE) -> list[dict[str, Any]]:
    """4. Top 10 countries by population."""
    conn = _get_connection(db_path)
    try:
        rows = conn.execute(
            """
            SELECT 
                d.common_name,
                d.cca3,
                d.region,
                d.capital,
                p.population,
                d.area_km2,
                ROUND(p.population_density, 2) AS population_density
            FROM dim_country d
            JOIN fact_population p ON d.country_id = p.country_id
            ORDER BY p.population DESC
            LIMIT 10
            """
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_top10_by_area(db_path: Path = DB_FILE) -> list[dict[str, Any]]:
    """5. Top 10 countries by area."""
    conn = _get_connection(db_path)
    try:
        rows = conn.execute(
            """
            SELECT 
                d.common_name,
                d.cca3,
                d.region,
                d.capital,
                d.area_km2,
                p.population,
                ROUND(p.population_density, 2) AS population_density
            FROM dim_country d
            JOIN fact_population p ON d.country_id = p.country_id
            WHERE d.area_km2 IS NOT NULL AND d.area_km2 > 0
            ORDER BY d.area_km2 DESC
            LIMIT 10
            """
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_countries_by_region(db_path: Path = DB_FILE) -> list[dict[str, Any]]:
    """6. Number of countries by region."""
    conn = _get_connection(db_path)
    try:
        rows = conn.execute(
            """
            SELECT 
                region,
                COUNT(*) AS country_count
            FROM dim_country
            GROUP BY region
            ORDER BY country_count DESC
            """
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_all_countries(region_filter: str | None = None, search: str | None = None, db_path: Path = DB_FILE) -> list[dict[str, Any]]:
    """7. Searchable and filterable country table."""
    query = """
        SELECT 
            d.country_id,
            d.cca3,
            d.common_name,
            d.official_name,
            d.capital,
            d.region,
            d.subregion,
            d.area_km2,
            p.population,
            ROUND(p.population_density, 2) AS population_density,
            d.landlocked,
            d.currencies_json,
            d.languages_json
        FROM dim_country d
        JOIN fact_population p ON d.country_id = p.country_id
        WHERE 1=1
    """
    params: list[Any] = []
    if region_filter and region_filter.strip().lower() != "all":
        query += " AND LOWER(d.region) = LOWER(?)"
        params.append(region_filter.strip())

    if search and search.strip():
        term = f"%{search.strip().lower()}%"
        query += " AND (LOWER(d.common_name) LIKE ? OR LOWER(d.cca3) LIKE ? OR LOWER(d.capital) LIKE ?)"
        params.extend([term, term, term])

    query += " ORDER BY p.population DESC"

    conn = _get_connection(db_path)
    try:
        rows = conn.execute(query, params).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            try:
                curr_dict = json.loads(d["currencies_json"] or "{}")
                d["currencies_display"] = ", ".join(f"{k} ({v.get('symbol', '')})" if isinstance(v, dict) else k for k, v in curr_dict.items()) or "None"
            except Exception:
                d["currencies_display"] = "-"

            try:
                lang_dict = json.loads(d["languages_json"] or "{}")
                d["languages_display"] = ", ".join(lang_dict.values()) if isinstance(lang_dict, dict) else str(lang_dict)
            except Exception:
                d["languages_display"] = "-"

            result.append(d)
        return result
    finally:
        conn.close()


def get_latest_etl_log(db_path: Path = DB_FILE) -> dict[str, Any] | None:
    """Retrieves the latest audit run log."""
    conn = _get_connection(db_path)
    try:
        row = conn.execute("SELECT * FROM etl_run_log ORDER BY run_id DESC LIMIT 1").fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_dashboard_summary(db_path: Path = DB_FILE) -> dict[str, Any]:
    """Prepares all analytical payloads needed for the web dashboard."""
    return {
        "kpis": {
            "total_countries": get_country_count(db_path),
            "total_population": get_total_population(db_path),
            "total_area_km2": get_total_area(db_path),
        },
        "population_by_region": get_population_by_region(db_path),
        "countries_by_region": get_countries_by_region(db_path),
        "top10_population": get_top10_by_population(db_path),
        "top10_area": get_top10_by_area(db_path),
        "latest_run": get_latest_etl_log(db_path),
    }
