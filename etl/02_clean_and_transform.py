import pandas as pd
import numpy as np
import re
import logging
from pathlib import Path
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.db_config import RAW_DATA_DIR, CLEAN_DATA_DIR
from utils.logger import setup_logger

logger = setup_logger("02_transform")

def clean_year(year_str):
    """
    Standardize year formats:
    Mar-24 -> Mar 2024
    TTM -> TTM
    """
    if pd.isna(year_str) or str(year_str).strip() == '':
        return None
    
    s = str(year_str).strip()
    if s.upper() == 'TTM':
        return 'TTM'
    
    # Match Month-Year (e.g., Mar-24)
    match = re.match(r'([A-Za-z]+)-(\d{2})', s)
    if match:
        month = match.group(1)
        year_short = match.group(2)
        year_long = f"20{year_short}" if int(year_short) < 50 else f"19{year_short}"
        return f"{month} {year_long}"
    
    return s

def parse_analysis_string(s):
    """
    Parse "10 Years: 11%" -> period: 10, value: 0.11
    """
    if pd.isna(s) or str(s).strip() == '':
        return None, None
    
    match = re.search(r'(\d+)\s*Years?:\s*(-?\d+\.?\d*)%', str(s), re.IGNORECASE)
    if match:
        period = int(match.group(1))
        value = float(match.group(2)) / 100.0
        return period, value
    return None, None

def calculate_metrics(df_pl, df_bs, df_cf):
    """
    Compute derived metrics across dataframes.
    """
    # Merge for computation
    # This assumes company_id and year_id are present and aligned
    # For now, we perform local calculations within dataframes where possible
    
    # 1. Profit Loss Metrics
    if 'revenue' in df_pl.columns and 'net_profit' in df_pl.columns:
        df_pl['net_profit_margin_pct'] = (df_pl['net_profit'] / df_pl['revenue']) * 100
        
    if 'expenses' in df_pl.columns and 'revenue' in df_pl.columns:
        df_pl['expense_ratio_pct'] = (df_pl['expenses'] / df_pl['revenue']) * 100

    # 2. Balance Sheet Metrics
    if 'total_liabilities' in df_pl.columns and 'equity_capital' in df_bs.columns:
        # Complex multi-table joins would happen here in the main loop
        pass

    return df_pl, df_bs, df_cf

def normalize_columns(df):
    """
    Standardize column names: lowercase, strip, replace spaces with underscores.
    Handles common aliases for financial data.
    """
    df.columns = [c.strip().lower().replace(' ', '_').replace('.', '') for c in df.columns]
    
    # Alias Mapping
    alias_map = {
        'symbol': ['company_id', 'ticker', 'stock_symbol', 'id'],
        'revenue': ['sales', 'total_income', 'revenue_from_operations', 'turnover'],
        'net_profit': ['pat', 'profit_after_tax', 'net_income'],
        'expenses': ['total_expenses', 'expenditure'],
        'operating_profit': ['ebitda', 'pbit'],
        'borrowings': ['total_debt', 'debt', 'long_term_borrowings'],
        'equity_capital': ['share_capital'],
        'reserves': ['retained_earnings', 'reserves_and_surplus']
    }
    
    for standard, aliases in alias_map.items():
        if standard not in df.columns:
            for alias in aliases:
                if alias in df.columns:
                    logger.info(f"Mapping alias '{alias}' to '{standard}'")
                    # If we are mapping id/company_id to symbol, we want to keep the original for now
                    # but ensure 'symbol' exists
                    df[standard] = df[alias]
                    break
    return df

def extract_fiscal_year(period_str):
    if pd.isna(period_str) or str(period_str).strip() == '':
        return None
    match = re.search(r'(\d{4})', str(period_str))
    if match:
        return int(match.group(1))
    return None

def transform_data():
    logger.info("Starting transformation process")
    
    # 1. Load Data
    try:
        companies = pd.read_csv(RAW_DATA_DIR / "companies.csv")
        pl = pd.read_csv(RAW_DATA_DIR / "profitandloss.csv")
        bs = pd.read_csv(RAW_DATA_DIR / "balancesheet.csv")
        cf = pd.read_csv(RAW_DATA_DIR / "cashflow.csv")
        analysis = pd.read_csv(RAW_DATA_DIR / "analysis.csv")
    except Exception as e:
        logger.error(f"Error loading raw files: {e}")
        return

    # 2. Basic Cleaning and Normalization
    dataframes = {
        'companies': companies,
        'pl': pl,
        'bs': bs,
        'cf': cf,
        'analysis': analysis
    }
    
    for name, df in dataframes.items():
        # Strip strings and handle whitespace
        df.replace([r'\r', r'\n', r'\t'], '', regex=True, inplace=True)
        # Handle 'NULL' strings
        df.replace(['NULL', 'Null', 'nan', ''], np.nan, inplace=True)
        # Normalize column names
        dataframes[name] = normalize_columns(df)

    companies, pl, bs, cf, analysis = dataframes.values()

    # 3. Specific Transformations
    # Standardize 'period_name' and 'fiscal_year' across all fact dataframes
    for name, df in [('pl', pl), ('bs', bs), ('cf', cf), ('analysis', analysis)]:
        if 'period_name' not in df.columns:
            if 'year' in df.columns:
                df['period_name'] = df['year'].apply(clean_year)
            elif 'fiscal_year' in df.columns:
                df['period_name'] = 'Mar ' + df['fiscal_year'].astype(str) # Default to March
        else:
            df['period_name'] = df['period_name'].apply(clean_year)
        
        if 'fiscal_year' not in df.columns and 'period_name' in df.columns:
            df['fiscal_year'] = df['period_name'].apply(extract_fiscal_year)

    # Ensure required columns for metrics exist
    required_pl = ['net_profit', 'revenue']
    if all(col in pl.columns for col in required_pl):
        pl['net_profit_margin_pct'] = (pl['net_profit'] / pl['revenue'].replace(0, np.nan)) * 100
    else:
        missing = [c for c in required_pl if c not in pl.columns]
        logger.warning(f"Missing columns in P&L for metrics: {missing}. Available: {list(pl.columns)}")

    # Debt to Equity
    if 'borrowings' in bs.columns and 'equity_capital' in bs.columns:
        reserves = bs['reserves'] if 'reserves' in bs.columns else 0
        bs['debt_to_equity'] = (bs['borrowings'] / (bs['equity_capital'] + reserves).replace(0, np.nan))
    
    # Free Cash Flow
    if 'operating_cash_flow' in cf.columns and 'investing_cash_flow' in cf.columns:
        cf['free_cash_flow'] = cf['operating_cash_flow'] + cf['investing_cash_flow']
    elif 'net_cash_flow' in cf.columns:
        cf['free_cash_flow'] = cf['net_cash_flow'] # Fallback if specific flows missing

    # 4. Create proper fact_analysis from company metrics
    # Take latest metrics from companies and assign to latest year in PL
    if not pl.empty and not companies.empty:
        latest_pl = pl.sort_values(['symbol', 'fiscal_year'], ascending=[True, False]).drop_duplicates('symbol')
        analysis_new = companies[['symbol', 'face_value', 'book_value', 'roce_percentage', 'roe_percentage']].copy()
        analysis_new.rename(columns={
            'roce_percentage': 'roce_pct',
            'roe_percentage': 'roe_pct'
        }, inplace=True)
        
        # Merge with latest year info
        analysis_new = analysis_new.merge(latest_pl[['symbol', 'fiscal_year', 'period_name']], on='symbol', how='left')
        
        # Add missing columns required by schema/scoring engine
        for col in ['market_cap', 'current_price', 'stock_pe', 'dividend_yield', 'interest_coverage']:
            analysis_new[col] = np.nan
            
        analysis = analysis_new # Replace the aggregated one with this structured one

    # 5. Save Cleaned Data
    CLEAN_DATA_DIR.mkdir(parents=True, exist_ok=True)
    companies.to_csv(CLEAN_DATA_DIR / "dim_company.csv", index=False)
    pl.to_csv(CLEAN_DATA_DIR / "fact_profit_loss.csv", index=False)
    bs.to_csv(CLEAN_DATA_DIR / "fact_balance_sheet.csv", index=False)
    cf.to_csv(CLEAN_DATA_DIR / "fact_cash_flow.csv", index=False)
    analysis.to_csv(CLEAN_DATA_DIR / "fact_analysis.csv", index=False)
    
    logger.info("Transformation completed successfully. Files saved to data/clean/")

if __name__ == "__main__":
    transform_data()
