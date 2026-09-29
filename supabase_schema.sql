-- ═══════════════════════════════════════════════════════════════
-- AeroResilience — Supabase Database Schema
-- Run this in Supabase SQL Editor (Dashboard → SQL Editor → New Query)
-- ═══════════════════════════════════════════════════════════════


-- ─── 1. Community Actions Table ──────────────────────────────
-- Stores all community environmental actions (tree planting, clean drives, etc.)

CREATE TABLE IF NOT EXISTS community_actions (
    id              BIGSERIAL PRIMARY KEY,
    action_type     VARCHAR(100) NOT NULL,
    location        VARCHAR(200) NOT NULL,
    impact_value    INTEGER DEFAULT 1 CHECK (impact_value > 0),
    description     TEXT,
    contributor     VARCHAR(100) DEFAULT 'Anonymous',
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for fast queries
CREATE INDEX idx_actions_created_at ON community_actions (created_at DESC);
CREATE INDEX idx_actions_type ON community_actions (action_type);
CREATE INDEX idx_actions_contributor ON community_actions (contributor);


-- ─── 2. AQI Readings Table ──────────────────────────────────
-- Stores historical air quality sensor readings per city

CREATE TABLE IF NOT EXISTS aqi_readings (
    id              BIGSERIAL PRIMARY KEY,
    city            VARCHAR(100) NOT NULL,
    aqi             INTEGER NOT NULL CHECK (aqi >= 0 AND aqi <= 500),
    pm25            REAL,
    pm10            REAL,
    no2             REAL,
    so2             REAL,
    co              REAL,
    o3              REAL,
    temperature     REAL,
    humidity        REAL,
    wind_speed      REAL,
    lat             DOUBLE PRECISION,
    lon             DOUBLE PRECISION,
    source          VARCHAR(50) DEFAULT 'simulated',
    recorded_at     TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for time-series queries
CREATE INDEX idx_readings_city ON aqi_readings (city);
CREATE INDEX idx_readings_recorded_at ON aqi_readings (recorded_at DESC);
CREATE INDEX idx_readings_city_time ON aqi_readings (city, recorded_at DESC);


-- ─── 3. Cities Table (Reference) ────────────────────────────
-- Master list of monitored cities with metadata

CREATE TABLE IF NOT EXISTS cities (
    id              SERIAL PRIMARY KEY,
    name            VARCHAR(100) UNIQUE NOT NULL,
    state           VARCHAR(100),
    country         VARCHAR(100) DEFAULT 'India',
    lat             DOUBLE PRECISION NOT NULL,
    lon             DOUBLE PRECISION NOT NULL,
    population      INTEGER,
    base_aqi        INTEGER DEFAULT 100,
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Seed with Indian cities
INSERT INTO cities (name, state, lat, lon, population, base_aqi) VALUES
    ('Delhi',      'Delhi',         28.6139, 77.2090, 32941000, 220),
    ('Mumbai',     'Maharashtra',   19.0760, 72.8777, 21297000, 120),
    ('Bangalore',  'Karnataka',     12.9716, 77.5946, 13193000, 75),
    ('Chennai',    'Tamil Nadu',    13.0827, 80.2707, 11503000, 90),
    ('Kolkata',    'West Bengal',   22.5726, 88.3639, 15134000, 160),
    ('Hyderabad',  'Telangana',     17.3850, 78.4867, 10534000, 95),
    ('Pune',       'Maharashtra',   18.5204, 73.8567,  7764000, 85),
    ('Ahmedabad',  'Gujarat',       23.0225, 72.5714,  8450000, 130),
    ('Jaipur',     'Rajasthan',     26.9124, 75.7873,  3963000, 140),
    ('Lucknow',    'Uttar Pradesh', 26.8467, 80.9462,  3382000, 180)
ON CONFLICT (name) DO NOTHING;


-- ─── 4. Alerts Table ─────────────────────────────────────────
-- Stores AQI threshold alerts and anomaly detections

CREATE TABLE IF NOT EXISTS alerts (
    id              BIGSERIAL PRIMARY KEY,
    city            VARCHAR(100) NOT NULL,
    alert_type      VARCHAR(50) NOT NULL,     -- 'threshold', 'anomaly', 'forecast'
    severity        VARCHAR(20) NOT NULL,      -- 'info', 'warning', 'critical'
    aqi_value       INTEGER,
    message         TEXT NOT NULL,
    is_resolved     BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    resolved_at     TIMESTAMPTZ
);

CREATE INDEX idx_alerts_city ON alerts (city);
CREATE INDEX idx_alerts_created_at ON alerts (created_at DESC);
CREATE INDEX idx_alerts_unresolved ON alerts (is_resolved) WHERE is_resolved = FALSE;


-- ═══════════════════════════════════════════════════════════════
-- ROW LEVEL SECURITY (RLS)
-- ═══════════════════════════════════════════════════════════════

-- Enable RLS on all tables
ALTER TABLE community_actions ENABLE ROW LEVEL SECURITY;
ALTER TABLE aqi_readings ENABLE ROW LEVEL SECURITY;
ALTER TABLE cities ENABLE ROW LEVEL SECURITY;
ALTER TABLE alerts ENABLE ROW LEVEL SECURITY;

-- Public read access (anyone can view data)
CREATE POLICY "Public read access on community_actions"
    ON community_actions FOR SELECT
    USING (true);

CREATE POLICY "Public insert on community_actions"
    ON community_actions FOR INSERT
    WITH CHECK (true);

CREATE POLICY "Public read access on aqi_readings"
    ON aqi_readings FOR SELECT
    USING (true);

CREATE POLICY "Public insert on aqi_readings"
    ON aqi_readings FOR INSERT
    WITH CHECK (true);

CREATE POLICY "Public read access on cities"
    ON cities FOR SELECT
    USING (true);

CREATE POLICY "Public read access on alerts"
    ON alerts FOR SELECT
    USING (true);

CREATE POLICY "Public insert on alerts"
    ON alerts FOR INSERT
    WITH CHECK (true);


-- ═══════════════════════════════════════════════════════════════
-- VIEWS (Convenience Queries)
-- ═══════════════════════════════════════════════════════════════

-- Latest AQI reading per city
CREATE OR REPLACE VIEW latest_aqi_per_city AS
SELECT DISTINCT ON (city)
    city, aqi, pm25, pm10, no2, so2, co, o3,
    temperature, humidity, wind_speed,
    lat, lon, source, recorded_at
FROM aqi_readings
ORDER BY city, recorded_at DESC;

-- Community impact summary
CREATE OR REPLACE VIEW community_impact_summary AS
SELECT
    action_type,
    COUNT(*) AS total_actions,
    SUM(impact_value) AS total_impact,
    COUNT(DISTINCT contributor) AS unique_contributors,
    MAX(created_at) AS last_action
FROM community_actions
GROUP BY action_type
ORDER BY total_impact DESC;

-- Daily AQI averages per city (for trend analysis)
CREATE OR REPLACE VIEW daily_aqi_avg AS
SELECT
    city,
    DATE(recorded_at) AS date,
    ROUND(AVG(aqi)) AS avg_aqi,
    ROUND(AVG(pm25)::numeric, 1) AS avg_pm25,
    ROUND(AVG(temperature)::numeric, 1) AS avg_temp,
    MIN(aqi) AS min_aqi,
    MAX(aqi) AS max_aqi,
    COUNT(*) AS readings_count
FROM aqi_readings
GROUP BY city, DATE(recorded_at)
ORDER BY city, date DESC;


-- ═══════════════════════════════════════════════════════════════
-- FUNCTIONS
-- ═══════════════════════════════════════════════════════════════

-- Function: Get AQI stats for a city in a date range
CREATE OR REPLACE FUNCTION get_city_aqi_stats(
    p_city VARCHAR,
    p_start TIMESTAMPTZ DEFAULT NOW() - INTERVAL '7 days',
    p_end TIMESTAMPTZ DEFAULT NOW()
)
RETURNS TABLE (
    avg_aqi NUMERIC,
    min_aqi INTEGER,
    max_aqi INTEGER,
    avg_pm25 NUMERIC,
    readings_count BIGINT,
    hours_above_200 BIGINT,
    hours_above_300 BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        ROUND(AVG(r.aqi)::numeric, 1),
        MIN(r.aqi),
        MAX(r.aqi),
        ROUND(AVG(r.pm25)::numeric, 1),
        COUNT(*),
        COUNT(*) FILTER (WHERE r.aqi > 200),
        COUNT(*) FILTER (WHERE r.aqi > 300)
    FROM aqi_readings r
    WHERE r.city = p_city
      AND r.recorded_at BETWEEN p_start AND p_end;
END;
$$ LANGUAGE plpgsql;
