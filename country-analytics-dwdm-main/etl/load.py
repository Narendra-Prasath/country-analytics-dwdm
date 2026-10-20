"""
ETL Load Module for Country Analytics.

Loads cleaned country dimensional and fact data into SQLite with full
idempotency (upserts on conflict), foreign key integrity, and audit logging.
"""

from __future__ import annotations

import datetime
import logging
from pathlib import Path
import sqlite3
from typing import Any

logger = logging.getLogger("country_analytics.load")

BASE_DIR = Path(__file__).resolve().parent.parent
DB_FILE = BASE_DIR / "database" / "country_analytics.db"
SCHEMA_FILE = BASE_DIR / "database" / "schema.sql"


def init_database(db_path: Path = DB_FILE, schema_path: Path = SCHEMA_FILE) -> None:
    """Initializes the database schema if tables do not exist."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if not schema_path.exists():
        raise FileNotFoundError(f"Schema file not found at {schema_path}")

    sql_script = schema_path.read_text(encoding="utf-8")
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(sql_script)
    finally:
        conn.close()
    logger.info("Database schema initialized at %s", db_path)


def load_countries(
    records: list[dict[str, Any]],
    source_type: str,
    duplicates_detected: int = 0,
    db_path: Path = DB_FILE,
) -> dict[str, Any]:
    """
    Loads transformed country records into dim_country and fact_population.
    Logs run metadata in etl_run_log.

    Returns:
        dict with load summary stats and run_id.
    """
    init_database(db_path)
    started_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
    loaded_count = 0

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON;")
    cur = conn.cursor()

    try:
        # Create run log entry
        cur.execute(
            """
            INSERT INTO etl_run_log (
                started_at, source_type, rows_extracted, rows_transformed, status, message
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                started_at,
                source_type,
                len(records) + duplicates_detected,
                len(records),
                "RUNNING",
                "ETL batch load in progress",
            ),
        )
        run_id = cur.lastrowid

        for item in records:
            # 1. Upsert into dim_country
            cur.execute(
                """
                INSERT INTO dim_country (
                    cca3, common_name, official_name, capital, region, subregion,
                    area_km2, latitude, longitude, landlocked, un_member, independent,
                    flag_description, currencies_json, languages_json, raw_json, updated_at
                ) VALUES (
                    :cca3, :common_name, :official_name, :capital, :region, :subregion,
                    :area_km2, :latitude, :longitude, :landlocked, :un_member, :independent,
                    :flag_description, :currencies_json, :languages_json, :raw_json, datetime('now')
                )
                ON CONFLICT(cca3) DO UPDATE SET
                    common_name = excluded.common_name,
                    official_name = excluded.official_name,
                    capital = excluded.capital,
                    region = excluded.region,
                    subregion = excluded.subregion,
                    area_km2 = excluded.area_km2,
                    latitude = excluded.latitude,
                    longitude = excluded.longitude,
                    landlocked = excluded.landlocked,
                    un_member = excluded.un_member,
                    independent = excluded.independent,
                    flag_description = excluded.flag_description,
                    currencies_json = excluded.currencies_json,
                    languages_json = excluded.languages_json,
                    raw_json = excluded.raw_json,
                    updated_at = datetime('now');
                """,
                item,
            )

            # Retrieve country_id
            cur.execute("SELECT country_id FROM dim_country WHERE cca3 = ?", (item["cca3"],))
            row = cur.fetchone()
            if not row:
                raise RuntimeError(f"Could not resolve country_id for cca3 '{item['cca3']}'")
            country_id = row[0]

            # 2. Upsert into fact_population
            cur.execute(
                """
                INSERT INTO fact_population (
                    country_id, population, population_density, updated_at
                ) VALUES (
                    ?, ?, ?, datetime('now')
                )
                ON CONFLICT(country_id) DO UPDATE SET
                    population = excluded.population,
                    population_density = excluded.population_density,
                    updated_at = datetime('now');
                """,
                (country_id, item["population"], item["population_density"]),
            )
            loaded_count += 1

        finished_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
        cur.execute(
            """
            UPDATE etl_run_log SET
                finished_at = ?,
                rows_loaded = ?,
                duplicates_detected = ?,
                status = 'SUCCESS',
                message = 'ETL pipeline completed successfully'
            WHERE run_id = ?;
            """,
            (finished_at, loaded_count, duplicates_detected, run_id),
        )
        conn.commit()
        logger.info("Successfully loaded %d records into database (run_id: %d)", loaded_count, run_id)

        return {
            "run_id": run_id,
            "status": "SUCCESS",
            "rows_loaded": loaded_count,
            "duplicates_detected": duplicates_detected,
            "started_at": started_at,
            "finished_at": finished_at,
        }

    except Exception as exc:
        conn.rollback()
        logger.error("Database load transaction failed: %s", exc)
        try:
            cur.execute(
                """
                UPDATE etl_run_log SET
                    finished_at = datetime('now'),
                    status = 'FAILED',
                    message = ?
                WHERE run_id = ?;
                """,
                (str(exc), run_id),
            )
            conn.commit()
        except Exception:
            pass
        raise
    finally:
        cur.close()
        conn.close()
