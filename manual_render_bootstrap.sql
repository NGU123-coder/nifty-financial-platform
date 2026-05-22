-- --- MANUAL RENDER BOOTSTRAP SQL ---
-- Execute this in your Render PostgreSQL Console to initialize warehouse tables and demo data.

-- 1. Create Core Dimensions
CREATE TABLE IF NOT EXISTS dim_sector (
    sector_id SERIAL PRIMARY KEY,
    sector_name VARCHAR(100) UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS dim_health_label (
    health_id SERIAL PRIMARY KEY,
    label_name VARCHAR(50) UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS dim_year (
    year_id SERIAL PRIMARY KEY,
    fiscal_year INTEGER NOT NULL,
    period_name VARCHAR(20) NOT NULL,
    sort_order INTEGER,
    UNIQUE(fiscal_year, period_name)
);

CREATE TABLE IF NOT EXISTS dim_company (
    company_id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) UNIQUE NOT NULL,
    company_name VARCHAR(255) NOT NULL,
    sector_id INTEGER REFERENCES dim_sector(sector_id),
    industry VARCHAR(255),
    listing_date DATE
);

-- 2. Create Fact Tables (Required for Views)
CREATE TABLE IF NOT EXISTS fact_profit_loss (
    id SERIAL PRIMARY KEY,
    company_id INTEGER REFERENCES dim_company(company_id),
    year_id INTEGER REFERENCES dim_year(year_id),
    revenue NUMERIC(18, 2),
    net_profit NUMERIC(18, 2),
    net_profit_margin_pct NUMERIC(18, 2),
    UNIQUE(company_id, year_id)
);

CREATE TABLE IF NOT EXISTS fact_ml_scores (
    id SERIAL PRIMARY KEY,
    company_id INTEGER REFERENCES dim_company(company_id),
    year_id INTEGER REFERENCES dim_year(year_id),
    health_id INTEGER REFERENCES dim_health_label(health_id),
    probability_score NUMERIC(5, 4),
    prediction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(company_id, year_id)
);

-- 3. Seed Demo Data
-- Labels
INSERT INTO dim_health_label (label_name) VALUES ('EXCELLENT'), ('GOOD'), ('AVERAGE'), ('POOR'), ('CRITICAL') ON CONFLICT DO NOTHING;

-- Sectors
INSERT INTO dim_sector (sector_name) VALUES ('Banking'), ('IT'), ('Automobile'), ('Energy') ON CONFLICT DO NOTHING;

-- Years
INSERT INTO dim_year (fiscal_year, period_name, sort_order) VALUES 
(2022, 'Mar 2022', 2022), 
(2023, 'Mar 2023', 2023), 
(2024, 'Mar 2024', 2024) ON CONFLICT DO NOTHING;

-- Companies
INSERT INTO dim_company (symbol, company_name, sector_id) VALUES 
('HDFCBANK', 'HDFC Bank Ltd', (SELECT sector_id FROM dim_sector WHERE sector_name='Banking')),
('TCS', 'Tata Consultancy Services', (SELECT sector_id FROM dim_sector WHERE sector_name='IT')),
('TATAMOTORS', 'Tata Motors Ltd', (SELECT sector_id FROM dim_sector WHERE sector_name='Automobile')) ON CONFLICT DO NOTHING;

-- Sample Scores (2024)
INSERT INTO fact_ml_scores (company_id, year_id, health_id, probability_score) VALUES 
((SELECT company_id FROM dim_company WHERE symbol='HDFCBANK'), (SELECT year_id FROM dim_year WHERE fiscal_year=2024), (SELECT health_id FROM dim_health_label WHERE label_name='EXCELLENT'), 0.9250),
((SELECT company_id FROM dim_company WHERE symbol='TCS'), (SELECT year_id FROM dim_year WHERE fiscal_year=2024), (SELECT health_id FROM dim_health_label WHERE label_name='GOOD'), 0.8120),
((SELECT company_id FROM dim_company WHERE symbol='TATAMOTORS'), (SELECT year_id FROM dim_year WHERE fiscal_year=2024), (SELECT health_id FROM dim_health_label WHERE label_name='AVERAGE'), 0.6540) ON CONFLICT DO NOTHING;

-- Indexes
CREATE INDEX IF NOT EXISTS idx_company_symbol ON dim_company(symbol);
CREATE INDEX IF NOT EXISTS idx_year_val ON dim_year(fiscal_year);
