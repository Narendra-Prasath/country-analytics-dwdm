"""Analytics package for Country Analytics."""
from analytics.queries import (
    get_country_count,
    get_total_population,
    get_population_by_region,
    get_countries_by_region,
    get_top10_by_population,
    get_top10_by_area,
    get_all_countries,
    get_dashboard_summary,
)

__all__ = [
    "get_country_count",
    "get_total_population",
    "get_population_by_region",
    "get_countries_by_region",
    "get_top10_by_population",
    "get_top10_by_area",
    "get_all_countries",
    "get_dashboard_summary",
]
