# file: etl/03_load_to_postgres.py
import pandas as pd
from sqlalchemy import create_engine, text
from config.db_config import DATABASE_URL
from utils.logger import setup_logger

logger = setup_logger('load')
engine = create_engine(DATABASE_URL)

def load_dimensions():
    # 1. Dim Sector
    df_sector = pd.read_csv('data/clean/dim_sector.csv')
    with engine.connect() as conn:
        for _, row in df_sector.iterrows():
            conn.execute(text("""
                INSERT INTO dim_sector (sector_name) VALUES (:s)
                ON CONFLICT (sector_name) DO NOTHING
            """), {"s": row['sector_name']})
        conn.commit()
    logger.info("Loaded dim_sector")

    # 2. Dim Year
    df_year = pd.read_csv('data/clean/dim_year.csv')
    with engine.connect() as conn:
        for _, row in df_year.iterrows():
            conn.execute(text("""
                INSERT INTO dim_year (fiscal_year, period_name, sort_order) 
                VALUES (:fy, :pn, :so)
                ON CONFLICT (fiscal_year, period_name) DO UPDATE SET sort_order = EXCLUDED.sort_order
            """), {"fy": row['fiscal_year'], "pn": row['period_name'], "so": row['sort_order']})
        conn.commit()
    logger.info("Loaded dim_year")

    # 3. Dim Company
    df_comp = pd.read_csv('data/clean/dim_company.csv')
    with engine.connect() as conn:
        for _, row in df_comp.iterrows():
            # Get sector_id
            res = conn.execute(text("SELECT sector_id FROM dim_sector WHERE sector_name = :s"), {"s": row['sector']})
            sector_id = res.scalar()
            
            conn.execute(text("""
                INSERT INTO dim_company (symbol, company_name, sector_id, industry)
                VALUES (:sym, :name, :sid, :ind)
                ON CONFLICT (symbol) DO UPDATE SET company_name = EXCLUDED.company_name, sector_id = EXCLUDED.sector_id
            """), {"sym": row['symbol'], "name": row['name'], "sid": sector_id, "ind": row['industry']})
        conn.commit()
    logger.info("Loaded dim_company")

def clear_facts():
    with engine.connect() as conn:
        conn.execute(text("TRUNCATE fact_profit_loss, fact_balance_sheet, fact_cash_flow CASCADE"))
        conn.commit()
    logger.info("Cleared fact tables")

def load_facts():
    clear_facts()
    # Helper to get mappings
    with engine.connect() as conn:
        comp_map = {r[0]: r[1] for r in conn.execute(text("SELECT symbol, company_id FROM dim_company")).fetchall()}
        year_map = {f"{r[0]}_{r[1]}": r[2] for r in conn.execute(text("SELECT fiscal_year, period_name, year_id FROM dim_year")).fetchall()}

    def load_table(csv_name, table_name, mapping_func):
        df = pd.read_csv(f'data/clean/{csv_name}.csv')
        
        # Drop duplicates in source data if any
        df = df.drop_duplicates(subset=['symbol', 'fiscal_year', 'period_name'])
        
        df['company_id'] = df['symbol'].map(comp_map)
        
        # Ensure fiscal_year is handled as int to match year_map keys
        df['fiscal_year_clean'] = pd.to_numeric(df['fiscal_year'], errors='coerce').fillna(0).astype(int).astype(str)
        df['year_key'] = df['fiscal_year_clean'] + "_" + df['period_name'].astype(str)
        df['year_id'] = df['year_key'].map(year_map)
        
        df = df.dropna(subset=['company_id', 'year_id'])
        
        if len(df) == 0:
            logger.warning(f"No rows to load for {table_name} after mapping company/year IDs")
            return
            
        # Get target columns from table
        cols = mapping_func(df)
        cols.to_sql(table_name, engine, if_exists='append', index=False, method='multi')
        logger.info(f"Loaded {len(cols)} rows into {table_name}")

    # P&L
    load_table('fact_profit_loss', 'fact_profit_loss', lambda df: df[['company_id', 'year_id', 'revenue', 'expenses', 'operating_profit', 'net_profit', 'eps', 'net_profit_margin_pct', 'expense_ratio_pct']])
    
    # BS
    load_table('fact_balance_sheet', 'fact_balance_sheet', lambda df: df[['company_id', 'year_id', 'equity_capital', 'reserves', 'borrowings', 'other_liabilities', 'total_liabilities', 'fixed_assets', 'cwip', 'investments', 'other_assets', 'total_assets', 'debt_to_equity']])

    # CF
    load_table('fact_cash_flow', 'fact_cash_flow', lambda df: df[['company_id', 'year_id', 'operating_cash_flow', 'investing_cash_flow', 'financing_cash_flow', 'net_cash_flow', 'free_cash_flow']])

if __name__ == "__main__":
    load_dimensions()
    load_facts()
