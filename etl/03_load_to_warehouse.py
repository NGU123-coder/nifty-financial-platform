import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
import logging
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.db_config import DATABASE_URL, CLEAN_DATA_DIR
from utils.logger import setup_logger

logger = setup_logger("03_load")

def get_engine():
    return create_engine(DATABASE_URL)

def get_table_columns(table_name):
    """Fetches column names for a given table from PostgreSQL."""
    engine = get_engine()
    query = f"""
    SELECT column_name 
    FROM information_schema.columns 
    WHERE table_schema = 'public' AND table_name = '{table_name}'
    AND (column_default IS NULL OR column_default NOT LIKE 'nextval%')
    """
    with engine.connect() as conn:
        result = conn.execute(text(query))
        return [row[0] for row in result.fetchall()]

def upsert_data(df, table_name, constraint_cols, update_cols):
    """
    Performs an UPSERT (Insert or Update) in PostgreSQL.
    """
    engine = get_engine()
    
    # 1. Deduplicate source data by constraints to avoid CardinalityViolation
    df = df.drop_duplicates(subset=constraint_cols, keep='last')
    
    # 2. Filter columns to match target table (excluding serial/auto-inc)
    target_cols = get_table_columns(table_name)
    df = df[[c for c in df.columns if c in target_cols]].copy()
    
    if df.empty:
        logger.warning(f"No matching columns found for table {table_name}. Target cols: {target_cols}, DF cols: {list(df.columns)}")
        return 0

    # Create temp table
    temp_table = f"temp_{table_name}"
    df.to_sql(temp_table, engine, if_exists='replace', index=False)
    
    # Construct UPSERT SQL
    set_clause = ", ".join([f"{col} = EXCLUDED.{col}" for col in update_cols if col in df.columns])
    if not set_clause:
        set_clause = f"{constraint_cols[0]} = EXCLUDED.{constraint_cols[0]}" # Fallback
        
    constraint_str = ", ".join(constraint_cols)
    
    upsert_sql = f"""
    INSERT INTO {table_name} ({", ".join(df.columns)})
    SELECT * FROM {temp_table}
    ON CONFLICT ({constraint_str})
    DO UPDATE SET {set_clause};
    """
    
    with engine.begin() as conn:
        result = conn.execute(text(upsert_sql))
        # Drop temp table
        conn.execute(text(f"DROP TABLE {temp_table}"))
        
    return result.rowcount

def load_warehouse():
    logger.info("Starting warehouse loading process")
    
    # 0. Ensure schema exists
    try:
        from db.init_db import init_db
        init_db()
    except Exception as e:
        logger.error(f"Error during schema initialization: {e}")

    engine = get_engine()
    
    # Load mappings
    def refresh_mappings():
        with engine.connect() as conn:
            c_map = {r[0]: r[1] for r in conn.execute(text("SELECT symbol, company_id FROM dim_company")).fetchall()}
            y_map = {f"{r[0]}_{r[1]}": r[2] for r in conn.execute(text("SELECT fiscal_year, period_name, year_id FROM dim_year")).fetchall()}
            s_map = {r[0]: r[1] for r in conn.execute(text("SELECT sector_name, sector_id FROM dim_sector")).fetchall()}
        return c_map, y_map, s_map

    comp_map, year_map, sector_map = refresh_mappings()

    # Define table load configurations
    load_configs = [
        # Dimensions
        ("dim_sector", "dim_sector.csv", ["sector_name"], ["sector_name"]),
        ("dim_company", "dim_company.csv", ["symbol"], ["company_name", "sector_id", "industry", "listing_date"]),
        ("dim_year", "dim_year.csv", ["fiscal_year", "period_name"], ["sort_order"]),
        
        # Facts
        ("fact_profit_loss", "fact_profit_loss.csv", ["company_id", "year_id"], 
         ["revenue", "expenses", "operating_profit", "net_profit", "eps", "net_profit_margin_pct", "expense_ratio_pct"]),
        
        ("fact_balance_sheet", "fact_balance_sheet.csv", ["company_id", "year_id"], 
         ["equity_capital", "reserves", "borrowings", "other_liabilities", "total_liabilities", "fixed_assets", "total_assets", "debt_to_equity"]),
        
        ("fact_cash_flow", "fact_cash_flow.csv", ["company_id", "year_id"], 
         ["operating_cash_flow", "investing_cash_flow", "financing_cash_flow", "net_cash_flow", "free_cash_flow"]),

        ("fact_analysis", "fact_analysis.csv", ["company_id", "year_id"],
         ["market_cap", "current_price", "stock_pe", "book_value", "dividend_yield", "roce_pct", "roe_pct", "interest_coverage"])
    ]
    
    stats = {"inserted_updated": 0, "failed": 0}

    for table, filename, constraints, updates in load_configs:
        file_path = CLEAN_DATA_DIR / filename
        if not file_path.exists():
            logger.warning(f"File not found, skipping: {file_path}")
            continue
            
        try:
            df = pd.read_csv(file_path)
            if df.empty: continue
            
            # Ensure required mapping columns exist
            if 'company_id' not in df.columns: df['company_id'] = np.nan
            if 'year_id' not in df.columns: df['year_id'] = np.nan
            
            # Map IDs if necessary
            if 'symbol' in df.columns and table != 'dim_company':
                df['company_id'] = df['symbol'].map(comp_map)
            
            if 'sector' in df.columns and table == 'dim_company':
                df['sector_id'] = df['sector'].map(sector_map)

            if 'fiscal_year' in df.columns and 'period_name' in df.columns:
                # Ensure types match for mapping
                df['fy_tmp'] = pd.to_numeric(df['fiscal_year'], errors='coerce').fillna(0).astype(int).astype(str)
                df['pn_tmp'] = df['period_name'].astype(str)
                df['year_key'] = df['fy_tmp'] + "_" + df['pn_tmp']
                df['year_id'] = df['year_key'].map(year_map)
            
            # Drop rows with missing required IDs for facts
            if table.startswith('fact_'):
                initial_len = len(df)
                df = df.dropna(subset=['company_id', 'year_id'])
                if len(df) < initial_len:
                    logger.warning(f"Dropped {initial_len - len(df)} rows from {table} due to missing ID mappings. Mapped: {len(df)}")

            if df.empty:
                logger.warning(f"No valid data to load for {table} after mapping.")
                continue
                
            rows = upsert_data(df, table, constraints, updates)
            logger.info(f"Successfully upserted {rows} rows into {table}")
            stats["inserted_updated"] += rows
            
            # Refresh mappings after loading dimensions
            if table.startswith('dim_'):
                comp_map, year_map, sector_map = refresh_mappings()

        except Exception as e:
            logger.error(f"Failed to load {table}: {e}", exc_info=True)
            stats["failed"] += 1

    logger.info(f"Load process completed. Stats: {stats}")

if __name__ == "__main__":
    load_warehouse()
