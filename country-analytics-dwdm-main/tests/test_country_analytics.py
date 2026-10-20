"""
Automated Test Suite for Country Analytics Project.

Tests:
1. ETL Extract, Transform, and Load functionality
2. Deduplication and data normalization
3. Analytical SQL queries
4. Web Dashboard HTTP endpoints
"""

from __future__ import annotations

import json
from pathlib import Path
import sqlite3
import unittest

from analytics.queries import (
    get_all_countries,
    get_countries_by_region,
    get_country_count,
    get_dashboard_summary,
    get_population_by_region,
    get_top10_by_area,
    get_top10_by_population,
    get_total_population,
)
from etl.extract import extract_countries
from etl.load import init_database, load_countries
from etl.transform import transform_countries
from web.app import app

BASE_DIR = Path(__file__).resolve().parent.parent
TEST_DB = BASE_DIR / "database" / "test_country_analytics.db"


class TestCountryAnalytics(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Ensure fresh test db
        if TEST_DB.exists():
            TEST_DB.unlink()

    @classmethod
    def tearDownClass(cls):
        if TEST_DB.exists():
            TEST_DB.unlink()

    def test_01_extract(self):
        """Test extraction fallback returns list of country records."""
        records, source = extract_countries()
        self.assertIsInstance(records, list)
        self.assertGreater(len(records), 0)
        self.assertIn("FALLBACK", source)

    def test_02_transform_and_deduplicate(self):
        """Test transformation normalizes fields and eliminates duplicate cca3."""
        sample_records = [
            {
                "cca3": "tst",
                "name": {"common": "Testland", "official": "State of Testland"},
                "capital": ["Test City"],
                "region": "Testing",
                "population": "1000000",
                "area": "50000",
            },
            {
                "cca3": "TST",  # Duplicate with different case
                "name": {"common": "Duplicate Testland"},
                "population": 2000000,
            },
        ]
        cleaned, metrics = transform_countries(sample_records)
        self.assertEqual(len(cleaned), 1)
        self.assertEqual(metrics["valid_count"], 1)
        self.assertEqual(metrics["duplicate_count"], 1)
        self.assertEqual(cleaned[0]["cca3"], "TST")
        self.assertEqual(cleaned[0]["population"], 1000000)
        self.assertEqual(cleaned[0]["population_density"], 20.0)

    def test_03_load_and_idempotency(self):
        """Test loading into SQLite and verify idempotency on repeated execution."""
        records, source = extract_countries()
        cleaned, metrics = transform_countries(records)

        # First load
        load_summary1 = load_countries(cleaned, source, metrics["duplicate_count"], db_path=TEST_DB)
        self.assertEqual(load_summary1["status"], "SUCCESS")
        count1 = get_country_count(db_path=TEST_DB)
        self.assertGreater(count1, 0)

        # Repeated load (Idempotency test)
        load_summary2 = load_countries(cleaned, source, metrics["duplicate_count"], db_path=TEST_DB)
        self.assertEqual(load_summary2["status"], "SUCCESS")
        count2 = get_country_count(db_path=TEST_DB)
        self.assertEqual(count1, count2, "Duplicate rows inserted on repeated ETL execution!")

    def test_04_analytics_queries(self):
        """Test all analytical queries return valid non-empty data."""
        total_countries = get_country_count(db_path=TEST_DB)
        total_pop = get_total_population(db_path=TEST_DB)
        pop_by_region = get_population_by_region(db_path=TEST_DB)
        countries_by_region = get_countries_by_region(db_path=TEST_DB)
        top10_pop = get_top10_by_population(db_path=TEST_DB)
        top10_area = get_top10_by_area(db_path=TEST_DB)
        filtered = get_all_countries(region_filter="Asia", search="India", db_path=TEST_DB)

        self.assertGreater(total_countries, 0)
        self.assertGreater(total_pop, 0)
        self.assertGreater(len(pop_by_region), 0)
        self.assertGreater(len(countries_by_region), 0)
        self.assertLessEqual(len(top10_pop), 10)
        self.assertLessEqual(len(top10_area), 10)
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0]["cca3"], "IND")

    def test_05_web_dashboard(self):
        """Test Flask web routes and APIs."""
        client = app.test_client()

        # HTML page
        resp_html = client.get("/")
        self.assertEqual(resp_html.status_code, 200)
        self.assertIn(b"Country Analytics", resp_html.data)

        # API summary
        resp_summary = client.get("/api/summary")
        self.assertEqual(resp_summary.status_code, 200)
        data = resp_summary.get_json()
        self.assertIn("kpis", data)
        self.assertIn("top10_population", data)

        # API countries
        resp_countries = client.get("/api/countries?region=Asia")
        self.assertEqual(resp_countries.status_code, 200)
        c_list = resp_countries.get_json()
        self.assertTrue(all(c["region"].lower() == "asia" for c in c_list))


if __name__ == "__main__":
    unittest.main()
