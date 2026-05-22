# B100 Intelligence: ETL Pipeline Guide

This guide describes how to operate the production-grade ETL pipeline for the financial analytics project.

## 1. Pipeline Architecture
The pipeline follows a standard **Extract, Transform, Load (ETL)** pattern:
1.  **Extract:** Parses MySQL/SQL dumps into raw CSV files.
2.  **Transform:** Cleans data, standardizes formats, and computes financial metrics.
3.  **Load:** Upserts cleaned data into the PostgreSQL star schema.

---

## 2. Execution Commands
Run the scripts in order from the project root:

```bash
# Step 1: Extract raw data from SQL dump
python etl/01_extract_from_mysql.py data/raw/dump.sql

# Step 2: Clean and transform data
python etl/02_clean_and_transform.py

# Step 3: Load to PostgreSQL warehouse
python etl/03_load_to_warehouse.py

# Step 4: Run Advanced ML Scoring Engine
python scoring/financial_scoring_engine.py
```

---

## 3. ML Scoring Engine (Advanced Analytics)
The `scoring/financial_scoring_engine.py` script provides the advanced analytics layer:
- **Multi-Pillar Scoring:** Profitability, Growth, Debt, Cash Flow, Dividend, and Trend.
- **Sector-Aware Ranking:** Ranks companies within their own sector for fair comparison.
- **Insight Generation:** Automatically generates Pros and Cons stored in `fact_pros_cons`.
- **Health Labels:** Categorizes companies (EXCELLENT to WEAK) based on weighted scores.

---

## 4. SQL Helper Queries (Validation)

### Check Row Counts across Schema
```sql
SELECT 
   (SELECT COUNT(*) FROM dim_company) AS companies,
   (SELECT COUNT(*) FROM fact_profit_loss) AS pl_rows,
   (SELECT COUNT(*) FROM fact_balance_sheet) AS bs_rows;
```

### Identify Orphaned Records (FK Integrity)
```sql
SELECT f.*
FROM fact_profit_loss f
LEFT JOIN dim_company c ON f.company_id = c.company_id
WHERE c.company_id IS NULL;
```

### Validate Latest ML Scores
```sql
SELECT symbol, probability_score, prediction_date
FROM fact_ml_scores f
JOIN dim_company c ON f.company_id = c.company_id
ORDER BY prediction_date DESC
LIMIT 10;
```

---

## 4. Error Handling Strategy
- **Logging:** All scripts log to `logs/etl.log`.
- **Validation:** Stage 2 performs data type validation and range checks.
- **UPSERT Logic:** Stage 3 uses `ON CONFLICT` to prevent duplicates and allow re-runs.
- **Atomic Loads:** Stage 3 uses database transactions (`engine.begin()`) to ensure partial loads don't leave the database in an inconsistent state.

---

## 5. Data Quality Reporting
After each run, the `logs/etl.log` will contain a summary:
- **Extraction:** Total rows found per table.
- **Transformation:** Number of rows cleaned, missing values identified.
- **Loading:** Total rows inserted vs. updated vs. failed.

---

## 6. Directory Structure
```text
nifty-financial-platform/
├── config/
│   └── db_config.py      # Connection settings
├── data/
│   ├── raw/              # Extracted SQL data
│   └── clean/            # Transformed CSVs
├── etl/
│   ├── 01_extract_sql.py # Stage 1
│   ├── 02_transform.py   # Stage 2
│   └── 03_load.py        # Stage 3
├── utils/
│   ├── logger.py         # Logging setup
│   └── helpers.py        # Utility functions
└── logs/
    └── etl.log           # Operation history
```
