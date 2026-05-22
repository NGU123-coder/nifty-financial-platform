-- DIM TABLES
CREATE TABLE IF NOT EXISTS dim_sector (
    sector_id SERIAL PRIMARY KEY,
    sector_name VARCHAR(100) UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS dim_health_label (
    health_id SERIAL PRIMARY KEY,
    label_name VARCHAR(50) UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS dim_company (
    company_id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) UNIQUE NOT NULL,
    company_name VARCHAR(255) NOT NULL,
    sector_id INTEGER REFERENCES dim_sector(sector_id),
    industry VARCHAR(255),
    listing_date DATE
);

CREATE TABLE IF NOT EXISTS dim_year (
    year_id SERIAL PRIMARY KEY,
    fiscal_year INTEGER NOT NULL,
    period_name VARCHAR(20) NOT NULL, -- e.g., 'Mar 2024'
    sort_order INTEGER,
    UNIQUE(fiscal_year, period_name)
);

-- FACT TABLES
CREATE TABLE IF NOT EXISTS fact_profit_loss (
    id SERIAL PRIMARY KEY,
    company_id INTEGER REFERENCES dim_company(company_id),
    year_id INTEGER REFERENCES dim_year(year_id),
    revenue NUMERIC(18, 2),
    expenses NUMERIC(18, 2),
    operating_profit NUMERIC(18, 2),
    net_profit NUMERIC(18, 2),
    eps NUMERIC(18, 2),
    dividend_payout_pct NUMERIC(18, 2),
    net_profit_margin_pct NUMERIC(18, 2),
    expense_ratio_pct NUMERIC(18, 2),
    UNIQUE(company_id, year_id)
);

CREATE TABLE IF NOT EXISTS fact_balance_sheet (
    id SERIAL PRIMARY KEY,
    company_id INTEGER REFERENCES dim_company(company_id),
    year_id INTEGER REFERENCES dim_year(year_id),
    equity_capital NUMERIC(18, 2),
    reserves NUMERIC(18, 2),
    borrowings NUMERIC(18, 2),
    other_liabilities NUMERIC(18, 2),
    total_liabilities NUMERIC(18, 2),
    fixed_assets NUMERIC(18, 2),
    cwip NUMERIC(18, 2),
    investments NUMERIC(18, 2),
    other_assets NUMERIC(18, 2),
    total_assets NUMERIC(18, 2),
    debt_to_equity NUMERIC(18, 2),
    UNIQUE(company_id, year_id)
);

CREATE TABLE IF NOT EXISTS fact_cash_flow (
    id SERIAL PRIMARY KEY,
    company_id INTEGER REFERENCES dim_company(company_id),
    year_id INTEGER REFERENCES dim_year(year_id),
    operating_cash_flow NUMERIC(18, 2),
    investing_cash_flow NUMERIC(18, 2),
    financing_cash_flow NUMERIC(18, 2),
    net_cash_flow NUMERIC(18, 2),
    free_cash_flow NUMERIC(18, 2),
    UNIQUE(company_id, year_id)
);

CREATE TABLE IF NOT EXISTS fact_analysis (
    id SERIAL PRIMARY KEY,
    company_id INTEGER REFERENCES dim_company(company_id),
    year_id INTEGER REFERENCES dim_year(year_id),
    market_cap NUMERIC(18, 2),
    current_price NUMERIC(18, 2),
    high_low VARCHAR(50),
    stock_pe NUMERIC(18, 2),
    book_value NUMERIC(18, 2),
    dividend_yield NUMERIC(18, 2),
    roce_pct NUMERIC(18, 2),
    roe_pct NUMERIC(18, 2),
    face_value NUMERIC(18, 2),
    interest_coverage NUMERIC(18, 2),
    UNIQUE(company_id, year_id)
);

CREATE TABLE IF NOT EXISTS fact_pros_cons (
    id SERIAL PRIMARY KEY,
    company_id INTEGER REFERENCES dim_company(company_id),
    type VARCHAR(10) CHECK (type IN ('PROS', 'CONS')),
    point TEXT
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

-- INDEXES
CREATE INDEX IF NOT EXISTS idx_company_symbol ON dim_company(symbol);
CREATE INDEX IF NOT EXISTS idx_year_val ON dim_year(fiscal_year);
CREATE INDEX IF NOT EXISTS idx_pl_company_year ON fact_profit_loss(company_id, year_id);
CREATE INDEX IF NOT EXISTS idx_bs_company_year ON fact_balance_sheet(company_id, year_id);
