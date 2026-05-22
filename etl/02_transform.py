import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)

def clean_year_format(year_val):
    """
    Standardizes year formats like 'Mar-13' to 'Mar 2013' if needed,
    or just returns as is if it matches dim_year.period_name.
    Actually, let's just ensure it's a string and stripped.
    """
    if pd.isna(year_val):
        return None
    return str(year_val).strip()

def handle_nulls(df):
    """
    Handles null values by filling with 0 for numeric columns
    that are part of calculations.
    """
    # Identify numeric columns
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    df[numeric_cols] = df[numeric_cols].fillna(0)
    return df

def normalize_columns(df, mapping):
    """
    Normalizes column names based on a mapping of aliases.
    """
    for target, aliases in mapping.items():
        for alias in aliases:
            if alias in df.columns and target not in df.columns:
                df = df.rename(columns={alias: target})
    return df

def transform_profit_loss(df):
    """
    Transforms P&L data and computes net_profit_margin_pct and expense_ratio_pct.
    """
    df = df.copy()
    
    # 1. Normalize aliases early
    alias_mapping = {
        'revenue': ['sales', 'turnover', 'total_income', 'revenue_from_operations'],
        'dividend_payout_pct': ['dividend_payout', 'dividend_pct'],
    }
    df = normalize_columns(df, alias_mapping)
    
    # 2. Defensive check for required columns
    required = ['revenue', 'net_profit', 'expenses']
    missing = [c for c in required if c not in df.columns]
    if missing:
        logger.warning(f"Missing required columns in P&L: {missing}. Filling with 0.")
        for c in missing:
            df[c] = 0

    df = handle_nulls(df)
    
    # 3. Calculations using normalized names
    # net_profit_margin_pct = (net_profit / revenue) * 100
    df['net_profit_margin_pct'] = np.where(
        df['revenue'] != 0, 
        (df['net_profit'] / df['revenue']) * 100, 
        0
    )
    
    # expense_ratio_pct = (expenses / revenue) * 100
    df['expense_ratio_pct'] = np.where(
        df['revenue'] != 0, 
        (df['expenses'] / df['revenue']) * 100, 
        0
    )
    
    return df

def transform_balance_sheet(df):
    """
    Transforms Balance Sheet data and computes debt_to_equity.
    """
    df = df.copy()
    df = handle_nulls(df)
    
    # debt_to_equity = borrowings / (equity_capital + reserves)
    denominator = df['equity_capital'] + df['reserves']
    df['debt_to_equity'] = np.where(
        denominator != 0, 
        df['borrowings'] / denominator, 
        0
    )
    
    # Rename columns to match schema
    df = df.rename(columns={
        'other_asset': 'other_assets'
    })
    
    return df

def transform_cash_flow(df):
    """
    Transforms Cash Flow data and computes free_cash_flow.
    """
    df = df.copy()
    df = handle_nulls(df)
    
    # free_cash_flow = operating_activity + investing_activity
    # (assuming investing_activity is mostly CAPEX and negative)
    df['free_cash_flow'] = df['operating_activity'] + df['investing_activity']
    
    # Rename columns to match schema
    df = df.rename(columns={
        'operating_activity': 'operating_cash_flow',
        'investing_activity': 'investing_cash_flow',
        'financing_activity': 'financing_cash_flow'
    })
    
    return df

def transform_analysis(df_pl, df_comp):
    """
    Transforms Analysis data and computes interest_coverage.
    Note: This is derived from P&L as the raw analysis.csv has growth rates.
    """
    # We use df_pl to get interest_coverage per year
    df = df_pl.copy()
    
    # interest_coverage = operating_profit / interest
    df['interest_coverage'] = np.where(
        df['interest'] != 0, 
        df['operating_profit'] / df['interest'], 
        df['operating_profit'] # If interest is 0, coverage is effectively the profit (or infinite)
    )
    
    # We might want to join with some static data from companies.csv if needed
    # but companies.csv is not time-series. For now, let's just use P&L derived data.
    
    # Selected columns for fact_analysis
    # We don't have all columns like market_cap, so we'll leave them as NaN
    cols = ['company_id', 'year', 'interest_coverage']
    return df[cols]

def extract_fy(s):
    """
    Extracts fiscal year from a string like 'Mar 2024'.
    """
    import re
    if pd.isna(s) or str(s).strip() == '':
        return None
    match = re.search(r'(\d{4})', str(s))
    if match:
        return int(match.group(1))
    return None

def map_dimensions(df, company_map, year_map):
    """
    Maps company_id (symbol) and year to their database IDs.
    """
    df = df.copy()
    
    # Initialize mapping columns to None
    df['company_id_int'] = None
    df['year_id'] = None
    
    # 1. Map Company
    if 'company_id' in df.columns:
        df['company_id_int'] = df['company_id'].map(company_map)
    
    # 2. Map Year
    if 'year' in df.columns:
        df['fiscal_year_tmp'] = df['year'].apply(extract_fy)
        # Handle 'TTM' or other cases if needed
        df['year_key'] = df['fiscal_year_tmp'].astype(str) + "_" + df['year'].astype(str)
        df['year_id'] = df['year_key'].map(year_map)
        
        # Fallback if year_key mapping fails (maybe period_name is just year)
        missing_mask = df['year_id'].isna() & df['year'].notna()
        if missing_mask.any():
            df.loc[missing_mask, 'year_id'] = df.loc[missing_mask, 'year'].map(year_map)
    
    # Drop rows that couldn't be mapped
    initial_len = len(df)
    df = df.dropna(subset=['company_id_int', 'year_id'])
    
    if len(df) < initial_len:
        logger.warning(f"Dropped {initial_len - len(df)} rows due to mapping failures")
        
    return df
