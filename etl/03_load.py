import os
import logging
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.dialects.postgresql import insert
from dotenv import load_dotenv

import sys
# Add the project root to sys.path to allow importing from the etl package
sys.path.append(os.getcwd())

# Import our custom modules using importlib because filenames start with numbers
import importlib
try:
    extract = importlib.import_module("etl.01_extract")
    transform = importlib.import_module("etl.02_transform")
except ImportError:
    # Fallback for when running from within the etl directory
    extract = importlib.import_module("01_extract")
    transform = importlib.import_module("02_transform")

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv(override=False)
DATABASE_URL = os.getenv("DATABASE_URL")

def get_engine():
    return create_engine(DATABASE_URL)

def get_dim_mappings(engine):
    """
    Fetches dim_company and dim_year to create lookup dictionaries.
    """
    with engine.connect() as conn:
        companies = pd.read_sql("SELECT company_id, symbol FROM dim_company", conn)
        years = pd.read_sql("SELECT year_id, fiscal_year, period_name FROM dim_year", conn)
        sectors = pd.read_sql("SELECT sector_id, sector_name FROM dim_sector", conn)
        
    company_map = dict(zip(companies['symbol'], companies['company_id']))
    year_map = {f"{r.fiscal_year}_{r.period_name}": r.year_id for _, r in years.iterrows()}
    # Also map just by period_name for backward compatibility or simple cases
    for _, r in years.iterrows():
        if r.period_name not in year_map:
            year_map[r.period_name] = r.year_id
            
    sector_map = dict(zip(sectors['sector_name'], sectors['sector_id']))
    
    return company_map, year_map, sector_map

def upsert_dataframe(df, table_name, engine, index_elements):
    """
    Performs an UPSERT (INSERT ... ON CONFLICT DO UPDATE) for a dataframe.
    """
    if df.empty:
        logger.warning(f"No data to load for {table_name}")
        return 0

    # Use SQLAlchemy Core to get table schema
    from sqlalchemy import MetaData, Table
    metadata = MetaData()
    metadata.reflect(bind=engine, only=[table_name])
    table = Table(table_name, metadata, autoload_with=engine)
    
    # Filter dataframe columns to only those that exist in the table
    # AND are not serial/auto-incrementing if not provided
    table_cols = [c.name for c in table.columns]
    
    # Exclude PKs that are usually SERIAL if not in dataframe
    # For dimension tables, we usually don't want to provide the ID
    pks = [c.name for c in table.primary_key.columns]
    
    cols_to_use = [c for c in df.columns if c in table_cols]
    df_filtered = df[cols_to_use].copy()
    
    # Drop duplicates to prevent CardinalityViolation in ON CONFLICT
    initial_count = len(df_filtered)
    df_filtered = df_filtered.drop_duplicates(subset=index_elements, keep='last')
    if len(df_filtered) < initial_count:
        logger.warning(f"Dropped {initial_count - len(df_filtered)} duplicate rows for {table_name}")
    
    # Also ensure all index_elements are present
    for col in index_elements:
        if col not in df_filtered.columns:
            logger.error(f"Index element {col} missing from filtered dataframe for {table_name}")
            return 0

    # Convert dataframe to list of dictionaries
    data = df_filtered.to_dict(orient='records')
    
    # Build the insert statement
    stmt = insert(table).values(data)
    
    # Build the update statement for conflict
    # Update all columns except index elements and primary keys
    update_dict = {
        c.name: stmt.excluded[c.name]
        for c in table.columns
        if c.name not in index_elements and c.name not in pks
    }
    
    if update_dict:
        upsert_stmt = stmt.on_conflict_do_update(
            index_elements=index_elements,
            set_=update_dict
        )
    else:
        # If no columns to update, just do nothing on conflict
        upsert_stmt = stmt.on_conflict_do_nothing(index_elements=index_elements)
    
    with engine.begin() as conn:
        result = conn.execute(upsert_stmt)
        
    logger.info(f"Successfully upserted {len(df_filtered)} rows into {table_name}")
    return len(df_filtered)

def load_dimensions(raw_data, engine):
    """
    Loads dimension tables from raw data.
    """
    logger.info("Loading Dimensions...")
    
    # 1. Load dim_sector
    if 'sector' in raw_data['companies'].columns:
        sectors = pd.DataFrame(raw_data['companies']['sector'].dropna().unique(), columns=['sector_name'])
        upsert_dataframe(sectors, 'dim_sector', engine, ['sector_name'])
    
    # Refresh sector map
    with engine.connect() as conn:
        sectors = pd.read_sql("SELECT sector_id, sector_name FROM dim_sector", conn)
    sector_map = dict(zip(sectors['sector_name'], sectors['sector_id']))

    # 2. Load dim_company
    df_comp = raw_data['companies'].copy()
    # Normalize company columns
    df_comp = transform.normalize_columns(df_comp, {
        'symbol': ['id', 'ticker', 'symbol'],
        'company_name': ['name', 'company_name']
    })
    
    if 'sector' in df_comp.columns:
        df_comp['sector_id'] = df_comp['sector'].map(sector_map)
    
    upsert_dataframe(df_comp, 'dim_company', engine, ['symbol'])

    # 3. Load dim_year
    # Collect all unique years across fact tables
    all_years = []
    for key in ['profit_loss', 'balance_sheet', 'cash_flow']:
        if 'year' in raw_data[key].columns:
            all_years.extend(raw_data[key]['year'].dropna().unique())
    
    unique_years = sorted(list(set(all_years)))
    
    df_years = pd.DataFrame(unique_years, columns=['period_name'])
    df_years['fiscal_year'] = df_years['period_name'].apply(transform.extract_fy)
    df_years = df_years.dropna(subset=['fiscal_year'])
    df_years['sort_order'] = df_years['fiscal_year']
    
    upsert_dataframe(df_years, 'dim_year', engine, ['fiscal_year', 'period_name'])

def run_etl():
    engine = get_engine()
    
    # 0. Initialize DB
    from db.init_db import init_db
    init_db()
    
    # 1. Extraction
    logger.info("Starting Extraction phase...")
    raw_data = extract.run_extraction()
    
    # 2. Load Dimensions first
    load_dimensions(raw_data, engine)
    
    # 3. Transformation
    logger.info("Starting Transformation phase...")
    
    # Standardize years first
    for key in ['profit_loss', 'balance_sheet', 'cash_flow']:
        if 'year' in raw_data[key].columns:
            raw_data[key]['year'] = raw_data[key]['year'].apply(transform.clean_year_format)
    
    # Fetch mappings
    company_map, year_map, sector_map = get_dim_mappings(engine)
    
    # Transform P&L
    df_pl = transform.transform_profit_loss(raw_data['profit_loss'])
    df_pl = transform.map_dimensions(df_pl, company_map, year_map)
    
    # Transform Balance Sheet
    df_bs = transform.transform_balance_sheet(raw_data['balance_sheet'])
    df_bs = transform.map_dimensions(df_bs, company_map, year_map)
    
    # Transform Cash Flow
    df_cf = transform.transform_cash_flow(raw_data['cash_flow'])
    df_cf = transform.map_dimensions(df_cf, company_map, year_map)
    
    # Transform Analysis (using P&L derived data)
    df_analysis_raw = transform.transform_analysis(raw_data['profit_loss'], raw_data['companies'])
    # Merge with static data from companies.csv for face_value, book_value etc.
    if not raw_data['companies'].empty:
        comp_static = raw_data['companies'][['id', 'face_value', 'book_value', 'roce_percentage', 'roe_percentage']].rename(columns={
            'id': 'company_id',
            'roce_percentage': 'roce_pct',
            'roe_percentage': 'roe_pct'
        })
        df_analysis_raw = df_analysis_raw.merge(comp_static, on='company_id', how='left')
    
    df_analysis = transform.map_dimensions(df_analysis_raw, company_map, year_map)
    
    # 4. Loading
    logger.info("Starting Loading phase...")
    
    # Prepare dataframes for DB (using company_id_int)
    def prep_for_db(df):
        df = df.copy()
        df['company_id'] = df['company_id_int']
        # Drop temporary columns and columns not in schema
        cols_to_drop = ['company_id_int', 'year', 'fiscal_year_tmp', 'year_key']
        if 'id' in df.columns: cols_to_drop.append('id')
        return df.drop(columns=[c for c in cols_to_drop if c in df.columns])

    counts = {}
    
    counts['fact_profit_loss'] = upsert_dataframe(
        prep_for_db(df_pl), 'fact_profit_loss', engine, ['company_id', 'year_id']
    )
    
    counts['fact_balance_sheet'] = upsert_dataframe(
        prep_for_db(df_bs), 'fact_balance_sheet', engine, ['company_id', 'year_id']
    )
    
    counts['fact_cash_flow'] = upsert_dataframe(
        prep_for_db(df_cf), 'fact_cash_flow', engine, ['company_id', 'year_id']
    )
    
    counts['fact_analysis'] = upsert_dataframe(
        prep_for_db(df_analysis), 'fact_analysis', engine, ['company_id', 'year_id']
    )
    
    print("\nETL Job Summary:")
    print("-" * 30)
    for table, count in counts.items():
        print(f"{table}: {count} rows processed")
    print("-" * 30)

if __name__ == "__main__":
    run_etl()
