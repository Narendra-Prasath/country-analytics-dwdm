"""
Unified Runner for Country Analytics Pipeline.

Executes:
1. Database initialization and ETL Pipeline (Extract -> Transform -> Load)
2. Data Validation Checks
3. Analytical Query Execution and Pretty-Printing to CLI
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from analytics.queries import (
    get_country_count,
    get_total_population,
    get_total_area,
    get_population_by_region,
    get_countries_by_region,
    get_top10_by_population,
    get_top10_by_area,
    get_latest_etl_log,
)
from etl.pipeline import run_etl


def format_number(val: int | float | None) -> str:
    if val is None:
        return "N/A"
    return f"{val:,}"


def print_table(headers: list[str], rows: list[list[Any]], title: str) -> None:
    print(f"\n=== {title} ===")
    col_widths = [len(h) for h in headers]
    for row in rows:
        for idx, val in enumerate(row):
            col_widths[idx] = max(col_widths[idx], len(str(val)))

    header_str = " | ".join(h.ljust(col_widths[i]) for i, h in enumerate(headers))
    sep_str = "-+-".join("-" * col_widths[i] for i in range(len(headers)))
    print(header_str)
    print(sep_str)
    for row in rows:
        print(" | ".join(str(val).ljust(col_widths[i]) for i, val in enumerate(row)))


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Country Analytics Pipeline & Reports")
    parser.add_argument("--api-url", type=str, default=None, help="Optional REST Countries API URL to fetch from")
    parser.add_argument("--skip-etl", action="store_true", help="Skip ETL and only run analytics queries")
    args = parser.parse_args()

    if not args.skip_etl:
        print("\n>>> STEP 1: EXECUTING ETL PIPELINE...")
        etl_result = run_etl(api_url=args.api_url)
        print(f"ETL Result: {etl_result['status']} | Loaded: {etl_result['rows_loaded']} rows | Run ID: {etl_result['run_id']}")

    print("\n>>> STEP 2: RUNNING ANALYTICAL VALIDATIONS...")
    total_countries = get_country_count()
    total_pop = get_total_population()
    total_area = get_total_area()
    latest_run = get_latest_etl_log()

    print(f"Total Countries in Database : {total_countries}")
    print(f"Total Population Represented: {format_number(total_pop)}")
    print(f"Total Land Area Represented : {format_number(total_area)} km²")
    if latest_run:
        print(f"Latest ETL Run Status       : {latest_run.get('status')} (Rows: {latest_run.get('rows_loaded')}, Duplicates: {latest_run.get('duplicates_detected')})")

    # Output 1 & 6: Countries by Region
    region_countries = get_countries_by_region()
    print_table(
        headers=["Region", "Country Count"],
        rows=[[r["region"], r["country_count"]] for r in region_countries],
        title="1. Number of Countries by Region",
    )

    # Output 3: Population by Region
    region_pops = get_population_by_region()
    print_table(
        headers=["Region", "Total Population", "Average Population"],
        rows=[[r["region"], format_number(r["total_population"]), format_number(r["avg_population"])] for r in region_pops],
        title="2. Population by Region",
    )

    # Output 4: Top 10 Countries by Population
    top_pops = get_top10_by_population()
    print_table(
        headers=["Rank", "Country", "CCA3", "Region", "Capital", "Population", "Density (per km²)"],
        rows=[
            [
                idx + 1,
                r["common_name"],
                r["cca3"],
                r["region"],
                r["capital"] or "N/A",
                format_number(r["population"]),
                format_number(r["population_density"]),
            ]
            for idx, r in enumerate(top_pops)
        ],
        title="3. Top 10 Countries by Population",
    )

    # Output 5: Top 10 Countries by Area
    top_areas = get_top10_by_area()
    print_table(
        headers=["Rank", "Country", "CCA3", "Region", "Area (km²)", "Population"],
        rows=[
            [
                idx + 1,
                r["common_name"],
                r["cca3"],
                r["region"],
                format_number(r["area_km2"]),
                format_number(r["population"]),
            ]
            for idx, r in enumerate(top_areas)
        ],
        title="4. Top 10 Countries by Land Area",
    )

    print("\n>>> ALL ANALYTICAL OUTPUTS SUCCESSFULLY COMPUTED FROM DATABASE.\n")


if __name__ == "__main__":
    main()
