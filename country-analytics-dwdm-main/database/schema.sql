-- Country Analytics Relational Schema (SQLite compatible)
-- Supports dimensional modeling: dim_country, fact_population, etl_run_log

PRAGMA foreign_keys = ON;

-- 1. Dimension: dim_country
CREATE TABLE IF NOT EXISTS dim_country (
    country_id INTEGER PRIMARY KEY AUTOINCREMENT,
    cca3 TEXT UNIQUE NOT NULL,
    common_name TEXT NOT NULL,
    official_name TEXT,
    capital TEXT,
    region TEXT NOT NULL,
    subregion TEXT,
    area_km2 REAL,
    latitude REAL,
    longitude REAL,
    landlocked INTEGER DEFAULT 0,
    un_member INTEGER DEFAULT 1,
    independent INTEGER DEFAULT 1,
    flag_description TEXT,
    currencies_json TEXT,
    languages_json TEXT,
    raw_json TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

-- Indexes for dim_country
CREATE INDEX IF NOT EXISTS idx_country_cca3 ON dim_country(cca3);
CREATE INDEX IF NOT EXISTS idx_country_region ON dim_country(region);
CREATE INDEX IF NOT EXISTS idx_country_subregion ON dim_country(subregion);
CREATE INDEX IF NOT EXISTS idx_country_name ON dim_country(common_name);

-- 2. Fact: fact_population
CREATE TABLE IF NOT EXISTS fact_population (
    country_id INTEGER PRIMARY KEY,
    population INTEGER NOT NULL,
    population_density REAL,
    updated_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (country_id) REFERENCES dim_country(country_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_fact_pop_population ON fact_population(population DESC);
CREATE INDEX IF NOT EXISTS idx_fact_pop_density ON fact_population(population_density DESC);

-- 3. Audit / Lineage: etl_run_log
CREATE TABLE IF NOT EXISTS etl_run_log (
    run_id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at TEXT DEFAULT (datetime('now')),
    finished_at TEXT,
    source_type TEXT,
    rows_extracted INTEGER,
    rows_transformed INTEGER,
    rows_loaded INTEGER,
    duplicates_detected INTEGER,
    status TEXT,
    message TEXT
);

-- 4. Analytical Views for Queries & Dashboard
CREATE VIEW IF NOT EXISTS view_country_overview AS
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
    d.latitude,
    d.longitude,
    d.landlocked,
    d.un_member,
    d.independent,
    d.currencies_json,
    d.languages_json,
    d.updated_at
FROM dim_country d
JOIN fact_population p ON d.country_id = p.country_id;

CREATE VIEW IF NOT EXISTS view_region_summary AS
SELECT 
    region,
    COUNT(country_id) AS total_countries,
    SUM(population) AS total_population,
    ROUND(SUM(area_km2), 2) AS total_area_km2,
    ROUND(AVG(population), 0) AS avg_population,
    ROUND(SUM(population) * 1.0 / NULLIF(SUM(area_km2), 0), 2) AS regional_density
FROM view_country_overview
GROUP BY region
ORDER BY total_population DESC;

CREATE VIEW IF NOT EXISTS view_top10_population AS
SELECT 
    common_name,
    cca3,
    region,
    population,
    area_km2,
    population_density
FROM view_country_overview
ORDER BY population DESC
LIMIT 10;

CREATE VIEW IF NOT EXISTS view_top10_area AS
SELECT 
    common_name,
    cca3,
    region,
    area_km2,
    population,
    population_density
FROM view_country_overview
WHERE area_km2 IS NOT NULL AND area_km2 > 0
ORDER BY area_km2 DESC
LIMIT 10;
