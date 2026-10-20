"""
Flask Web Dashboard Application for Country Analytics.

Serves an interactive web dashboard with:
- Executive KPI summary cards
- Interactive Chart.js visual charts (Population by Region, Countries by Region, Top 10 by Pop/Area)
- Real-time searchable and filterable country data table
- Interactive REST API endpoints
- In-browser ETL pipeline trigger
"""

from __future__ import annotations

import json
from pathlib import Path
from flask import Flask, jsonify, render_template, request

from analytics.queries import (
    get_all_countries,
    get_countries_by_region,
    get_country_count,
    get_dashboard_summary,
    get_population_by_region,
    get_top10_by_area,
    get_top10_by_population,
    get_total_area,
    get_total_population,
)
from etl.pipeline import run_etl

BASE_DIR = Path(__file__).resolve().parent.parent

app = Flask(
    __name__,
    template_folder=str(BASE_DIR / "web" / "templates"),
    static_folder=str(BASE_DIR / "web" / "static"),
)


@app.route("/")
def index():
    summary = get_dashboard_summary()
    countries = get_all_countries()
    regions = [r["region"] for r in summary["countries_by_region"]]
    return render_template(
        "dashboard.html",
        summary=summary,
        countries=countries,
        regions=regions,
    )


@app.route("/api/summary")
def api_summary():
    return jsonify(get_dashboard_summary())


@app.route("/api/countries")
def api_countries():
    region = request.args.get("region")
    search = request.args.get("search")
    return jsonify(get_all_countries(region_filter=region, search=search))


@app.route("/api/run-etl", methods=["POST"])
def api_trigger_etl():
    try:
        data = request.get_json(silent=True) or {}
        api_url = data.get("api_url")
        result = run_etl(api_url=api_url)
        return jsonify({"success": True, "result": result})
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


def create_app():
    return app


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
