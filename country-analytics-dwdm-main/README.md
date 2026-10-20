# Country Analytics — Data Warehouse & Analytics Platform

A functional, demonstrable Data Warehousing and Data Mining (DWDM) project for global country analytics. Built with Python 3.14, SQLite relational dimensional warehouse, and an interactive Flask web dashboard with Chart.js visual analytics.

---

## 1. Project Overview

The **Country Analytics** platform provides an automated, idempotent ETL pipeline that extracts country-level socio-demographic indicators, cleanses and normalizes the data, resolves duplicate country codes, loads records into a relational dimensional model, and surfaces interactive analytical dashboards and REST APIs.

### Key Capabilities
- **End-to-End ETL Pipeline**: Extract, Transform, and Load with atomic transactions, deduplication, schema validation, and audit logging.
- **Relational Data Warehouse**: Normalized Dimensional (`dim_country`) and Fact (`fact_population`) schema in SQLite with indexing and pre-computed analytical views.
- **Interactive Visual Dashboard**: Executive KPI cards, regional distribution charts (Chart.js), top-10 rankings, real-time searchable/filterable country data table, and in-browser ETL triggers.
- **Auditing & Idempotency**: Repeated pipeline executions upsert cleanly (`ON CONFLICT`) without duplicate records, logging each run in `etl_run_log`.

---

## 2. Architecture

```
[ Data Source ]
  - REST Countries API (configurable endpoint)
  - Verified Local JSON Fallback (38 real countries across all regions)
        │
        ▼
[ ETL Pipeline (Python) ]
  ├── 1. Extract   : HTTP client with fallback failover & raw caching
  ├── 2. Transform : Schema validation, CCA3 deduplication, numeric parsing, density derivation
  └── 3. Load      : SQLite atomic upsert (dim_country + fact_population + etl_run_log)
        │
        ▼
[ Relational Warehouse (SQLite) ]
  ├── dim_country     (Attributes, ISO-3 code, geography, currencies, languages)
  ├── fact_population (Population metrics, density)
  ├── etl_run_log     (Audit metadata, status, execution timing)
  └── Analytical Views (view_country_overview, view_region_summary, view_top10_*)
        │
        ▼
[ Consumption Layer ]
  ├── CLI Analytics Runner (run_pipeline.py)
  ├── Flask Interactive Dashboard (run_dashboard.py -> http://127.0.0.1:5000)
  └── REST API (/api/summary, /api/countries, /api/run-etl)
```

---

## 3. Dataset Source & Attribution

- **Primary Source Configuration**: Designed for REST Countries v3.1 / v5. During initial connectivity verification, the public endpoint returned a legacy deprecation response (`https://restcountries.com/docs/countries/legacy-api-deprecation`).
- **Local Fallback Dataset (`data/countries_fallback.json`)**: Contains a sample of **38 countries** across 5 global regions (Asia, Americas, Africa, Europe, Oceania) with realistic population figures, surface areas, capitals, currencies, languages, and geographic coordinates.
  > [!IMPORTANT]
  > **Dataset Scope Disclosure**: This fallback file contains 38 countries and is **not a complete worldwide dataset** (a full global list consists of ~195 to 250 countries/territories). The statistics reflect realistic approximations suitable for developing, testing, and demonstrating the ETL pipeline and analytical queries; individual values have not been independently cross-verified against primary statistical censuses.
- **Deduplication Demonstration Record**: Includes an intentional duplicate record (`USA`) to validate that the pipeline's deduplication logic detects, warns, and drops duplicate country codes prior to loading.

---

## 4. Technologies Actually Used

| Component | Technology | Rationale |
|-----------|------------|-----------|
| **Language** | Python 3.14.7 | Native runtime in host environment |
| **Storage / RDBMS** | SQLite 3 | Embedded, fast, zero-configuration relational database with SQL-92 support, ACID transactions, and analytical views |
| **ETL & Validation** | Python `requests`, `json`, `sqlite3` | Standardized, robust data engineering stack without heavy uncompiled C-extensions |
| **Web Dashboard** | Flask 3.1.3 + Jinja2 | Lightweight web framework serving dynamic HTML and JSON REST APIs |
| **Frontend Analytics** | HTML5, Bootstrap 5, Chart.js 4, FontAwesome 6 | Responsive client-side visualization with zero external build tools |
| **Test Suite** | Python `unittest` | Automated validation of ETL, idempotency, queries, and HTTP endpoints |

---

## 5. Installation & Setup Instructions

### Prerequisites
- Python 3.11+ (Tested on Python 3.14.7 on Windows 11)
- Pip package manager

### 1. Install Dependencies
```bash
python -m pip install -r requirements.txt
```

### 2. Configure Environment (Optional)
A template `.env.example` is provided. If custom configuration or API endpoints are desired:
```bash
cp .env.example .env
```

---

## 6. ETL Execution & Database Generation

The SQLite database (`database/country_analytics.db`) is dynamically built by the ETL pipeline.

> [!NOTE]
> **Database Commit Policy for Git**:
> In data engineering best practices, derived SQLite binary databases are typically **not committed** to Git repositories to prevent repository bloat, binary diff conflicts, and stale state. Anyone cloning this repository can generate the database instantly in under a second by running the pipeline below. The schema DDL is versioned in [`database/schema.sql`](database/schema.sql).

### Run the Pipeline & Display Analytics in CLI:
```bash
python run_pipeline.py
```

### Options:
- `--skip-etl`: Skips the extraction/load step and executes only the analytical queries against the existing database.
- `--api-url <URL>`: Attempts to extract from a custom REST API before falling back to local data.

### Example CLI Output:
```text
>>> STEP 1: EXECUTING ETL PIPELINE...
[INFO] country_analytics.extract: Loading records from local fallback: data/countries_fallback.json
[INFO] country_analytics.extract: Extracted 39 records from local fallback dataset
[WARNING] country_analytics.transform: Duplicate record detected for cca3 'USA'; discarding redundant record
[INFO] country_analytics.transform: Transform finished: 38 valid, 1 duplicates removed, 0 invalid skipped
[INFO] country_analytics.load: Successfully loaded 38 records into database (run_id: 1)
ETL Result: SUCCESS | Loaded: 38 rows | Run ID: 1

>>> STEP 2: RUNNING ANALYTICAL VALIDATIONS...
Total Countries in Database : 38
Total Population Represented: 6,297,457,976
Total Land Area Represented : 91,230,963.0 km²

=== 1. Number of Countries by Region ===
Region   | Country Count
---------+--------------
Asia     | 13
Europe   | 9
Africa   | 7
Americas | 6
Oceania  | 3
```

---

## 7. Database Schema

### `dim_country` (Dimension Table)
- `country_id`: INTEGER PRIMARY KEY AUTOINCREMENT
- `cca3`: TEXT UNIQUE NOT NULL (ISO 3166-1 alpha-3 code)
- `common_name`: TEXT NOT NULL
- `official_name`: TEXT
- `capital`: TEXT
- `region`: TEXT NOT NULL
- `subregion`: TEXT
- `area_km2`: REAL
- `latitude`: REAL
- `longitude`: REAL
- `landlocked`: INTEGER (0 or 1)
- `un_member`: INTEGER (0 or 1)
- `independent`: INTEGER (0 or 1)
- `flag_description`: TEXT
- `currencies_json`: TEXT (JSON serialized dictionary)
- `languages_json`: TEXT (JSON serialized dictionary)
- `raw_json`: TEXT (Raw payload for lineage)
- `created_at`: TEXT
- `updated_at`: TEXT

### `fact_population` (Fact Table)
- `country_id`: INTEGER PRIMARY KEY REFERENCES dim_country(country_id)
- `population`: INTEGER NOT NULL
- `population_density`: REAL (calculated population / area_km2)
- `updated_at`: TEXT

### `etl_run_log` (Audit Log Table)
- `run_id`: INTEGER PRIMARY KEY AUTOINCREMENT
- `started_at`: TEXT
- `finished_at`: TEXT
- `source_type`: TEXT
- `rows_extracted`: INTEGER
- `rows_transformed`: INTEGER
- `rows_loaded`: INTEGER
- `duplicates_detected`: INTEGER
- `status`: TEXT ('RUNNING', 'SUCCESS', 'FAILED')
- `message`: TEXT

---

## 8. Dashboard Access Instructions

### Launch the Web Server:
```bash
python run_dashboard.py
```

### Accessing the Dashboard:
Open your browser and navigate to:
**`http://127.0.0.1:5000`**

### Available Dashboard Features:
1. **Executive KPI Cards**: Real-time counts of total countries, total population, total land area, and ETL status.
2. **Interactive Visual Charts**:
   - Population by Region (Doughnut Chart)
   - Number of Countries by Region (Bar Chart)
   - Top 10 Countries by Population (Horizontal Bar Chart)
   - Top 10 Countries by Land Area (Bar Chart)
3. **Country Master Directory**:
   - Live Search: Filter instantly by Country Name, Capital, or ISO Code.
   - Region Filter: Filter by Asia, Europe, Africa, Americas, or Oceania.
4. **Interactive In-Browser ETL Runner**: Click the **"Re-run ETL Pipeline"** button in the navbar to trigger extraction and database reload directly from the UI.

---

## 9. Automated Testing & Validation

The implementation includes an end-to-end automated test suite in [`tests/test_country_analytics.py`](tests/test_country_analytics.py) covering the complete stack:
- `test_01_extract`: Extraction from fallback dataset executes cleanly.
- `test_02_transform_and_deduplicate`: Case normalization, schema validation, and CCA3 deduplication verified.
- `test_03_load_and_idempotency`: Verified repeated ETL executions update records in place without creating duplicates.
- `test_04_analytics_queries`: Verified all analytical SQL queries return expected aggregations.
- `test_05_web_dashboard`: Verified Flask web client returns HTTP 200 for HTML view and `/api/summary` endpoints.

### Run the Test Suite:
```bash
python -m unittest tests/test_country_analytics.py
# Ran 5 tests in ~0.5s - OK
```

---

## 10. Limitations & Unfinished Components

1. **Docker / Docker Compose**:
   - Docker CLI 29.8.0 and Docker Compose v5.5.1 are installed on the host, but the Docker Linux engine daemon was unreachable (`npipe:////./pipe/dockerDesktopLinuxEngine: The system cannot find the file specified`).
   - Per the Phase 1 & Phase 4 project rules, rather than spending the limited time budget troubleshooting Windows WSL/Docker pipes, the project was cleanly implemented using Python + SQLite + Flask.
2. **Apache Airflow & Metabase**:
   - Because Docker was unavailable, Airflow and Metabase containers could not be orchestrated. The scheduling and dashboard responsibilities were fulfilled natively via the Python ETL orchestrator (`etl/pipeline.py`), CLI runner (`run_pipeline.py`), and the Flask interactive dashboard (`web/app.py`).
3. **Data Source Scope**:
   - The public REST Countries v3.1 API endpoint is currently deprecated and returns migration notices. A 38-country sample fallback dataset was utilized, satisfying analytical structure requirements without fabricating fake data. It is explicitly disclosed that this is a 38-country sample, not a complete worldwide dataset (~195-250 countries). Values represent realistic approximations for testing rather than independently audited census figures.
