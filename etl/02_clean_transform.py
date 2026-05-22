import pandas as pd
import numpy as np
import os
from pathlib import Path
import re

def parse_year(year_val):
    """
    Parse year formats like 'Mar-24', 'Dec-2012', 'TTM'.
    Returns (fiscal_year, period_name)
    """
    s = str(year_val).strip()
    if not s or s.lower() in ['nan', 'none', 'null', '']:
        return np.nan, s
    
    if s.upper() == 'TTM':
        return 9999, 'TTM'  # Using 9999 as a special flag for TTM
    
    # Regex to find the year at the end of the string
    match = re.search(r'(\d{2,4})$', s)
    if match:
        y_str = match.group(1)
        if len(y_str) == 2:
            val = int(y_str)
            # Logic for 2-digit years (assuming 2000s)
            year_int = 2000 + val
            return year_int, s
        return int(y_str), s
    
    return np.nan, s

def clean_numeric(val):
    """
    Remove commas, handle parentheses for negative numbers, and convert to float.
    """
    if pd.isna(val):
        return np.nan
    if isinstance(val, (int, float)):
        return float(val)
    
    s = str(val).replace(',', '').strip()
    if s == '' or s.lower() in ['nan', 'none', '-', 'null']:
        return np.nan
        
    # Handle accounting format: (1,000.00) -> -1000.00
    if s.startswith('(') and s.endswith(')'):
        s = '-' + s[1:-1]
        
    try:
        return float(s)
    except ValueError:
        return np.nan

def compute_metrics(df):
    """
    Calculate required financial metrics if necessary columns exist.
    Handles division by zero and missing values.
    """
    # 1. Debt to Equity = borrowings / (equity_capital + reserves)
    if all(col in df.columns for col in ['borrowings', 'equity_capital', 'reserves']):
        equity_sum = df['equity_capital'].fillna(0) + df['reserves'].fillna(0)
        df['debt_to_equity'] = np.where(
            equity_sum != 0, 
            df['borrowings'].fillna(0) / equity_sum, 
            np.nan
        )

    # 2. Net Profit Margin = (net_profit / revenue) * 100
    if all(col in df.columns for col in ['net_profit', 'revenue']):
        df['net_profit_margin_pct'] = np.where(
            df['revenue'] != 0, 
            (df['net_profit'].fillna(0) / df['revenue']) * 100, 
            np.nan
        )

    # 3. Expense Ratio = (expenses / revenue) * 100
    if all(col in df.columns for col in ['expenses', 'revenue']):
        df['expense_ratio_pct'] = np.where(
            df['revenue'] != 0, 
            (df['expenses'].fillna(0) / df['revenue']) * 100, 
            np.nan
        )
    elif 'expense_ratio_pct' not in df.columns:
        df['expense_ratio_pct'] = np.nan

    # 4. Free Cash Flow = operating_cash_flow + investing_cash_flow
    if all(col in df.columns for col in ['operating_cash_flow', 'investing_cash_flow']):
        df['free_cash_flow'] = df['operating_cash_flow'].fillna(0) + df['investing_cash_flow'].fillna(0)

    # 5. Interest Coverage = operating_profit / interest
    if all(col in df.columns for col in ['operating_profit', 'interest']):
        df['interest_coverage'] = np.where(
            df['interest'] != 0, 
            df['operating_profit'].fillna(0) / df['interest'], 
            np.nan
        )
        
    return df

def generate_dim_sector(clean_dir):
    """
    Create a dimension table for sectors based on companies data.
    """
    companies_path = clean_dir / 'companies.csv'
    if not companies_path.exists():
        print("Warning: companies.csv not found. Skipping dim_sector generation.")
        return
    
    df = pd.read_csv(companies_path)
    
    # 1. Ensure sector column exists
    if 'sector' not in df.columns:
        df['sector'] = 'Unknown'
    else:
        df['sector'] = df['sector'].fillna('Unknown').astype(str).str.strip()
        
    # 2. Get unique sectors and assign IDs
    sectors = sorted(df['sector'].unique())
    dim_sector = pd.DataFrame({
        'sector_id': range(1, len(sectors) + 1),
        'sector_name': sectors
    })
    
    # 3. Save to clean directory
    dim_sector.to_csv(clean_dir / 'dim_sector.csv', index=False)
    print(f"Successfully generated dim_sector.csv with {len(dim_sector)} sectors.")

def generate_dim_company(clean_dir):
    """
    Create a dimension table for companies.
    """
    companies_path = clean_dir / 'companies.csv'
    if not companies_path.exists():
         return

    df = pd.read_csv(companies_path)
    
    dim_company = pd.DataFrame()
    dim_company['symbol'] = df['id'].astype(str).str.upper().str.strip()
    dim_company['name'] = df['company_name'].astype(str).str.strip()
    dim_company['sector'] = df.get('sector', 'Unknown')
    dim_company['industry'] = df.get('industry', 'Unknown')
    
    dim_company.to_csv(clean_dir / 'dim_company.csv', index=False)
    print(f"Successfully generated dim_company.csv with {len(dim_company)} rows.")

def generate_dim_year(clean_dir):
    """
    Create a dimension table for years based on all cleaned data.
    """
    year_data = set()
    
    # Iterate over all csv files in clean_dir
    for csv_file in clean_dir.glob('*.csv'):
        # Skip dimension tables
        if csv_file.name.startswith('dim_'):
            continue
            
        df = pd.read_csv(csv_file)
        if 'fiscal_year' in df.columns and 'period_name' in df.columns:
            # Extract unique (fiscal_year, period_name) pairs
            valid_rows = df[['fiscal_year', 'period_name']].dropna()
            for _, row in valid_rows.iterrows():
                year_data.add((int(row['fiscal_year']), str(row['period_name'])))
            
    if not year_data:
        print("Warning: No fiscal_year/period_name found. Skipping dim_year generation.")
        return
        
    # Sort by fiscal_year, and then by period_name
    sorted_years = sorted(list(year_data), key=lambda x: (x[0], x[1]))
    
    dim_year = pd.DataFrame(sorted_years, columns=['fiscal_year', 'period_name'])
    dim_year['year_id'] = range(1, len(dim_year) + 1)
    dim_year['sort_order'] = dim_year['year_id']
    
    # Save to clean directory
    dim_year.to_csv(clean_dir / 'dim_year.csv', index=False)
    print(f"Successfully generated dim_year.csv with {len(dim_year)} rows.")

def process_file(file_name, output_name, input_dir, output_dir):
    input_path = input_dir / file_name
    output_path = output_dir / output_name
    
    if not input_path.exists():
        print(f"Skipping {file_name}: File not found.")
        return

    # Read CSV
    df = pd.read_csv(input_path)
    
    # 1. Standardize Company ID to Symbol
    if 'company_id' in df.columns:
        df['symbol'] = df['company_id'].astype(str).str.upper().str.strip()
    elif 'id' in df.columns:
        df['symbol'] = df['id'].astype(str).str.upper().str.strip()
    
    # 2. Clean YEAR column
    if 'year' in df.columns:
        parsed_years = df['year'].apply(parse_year)
        df['fiscal_year'] = [p[0] for p in parsed_years]
        df['period_name'] = [p[1] for p in parsed_years]
        df['fiscal_year'] = pd.to_numeric(df['fiscal_year'], errors='coerce').astype('Int64')

    # 3. Convert numeric columns
    exclude_cols = ['company_id', 'id', 'year', 'period_name', 'fiscal_year', 'symbol', 'date', 'name', 'sector', 'industry', 'company_name']
    for col in df.columns:
        if col not in exclude_cols and df[col].dtype == 'object':
            df[col] = df[col].apply(clean_numeric)

    # Rename some columns to match load script expectations if they exist
    rename_map = {
        'net_profit_margin': 'net_profit_margin_pct',
        'sales': 'revenue',
        'operating_activity': 'operating_cash_flow',
        'investing_activity': 'investing_cash_flow',
        'financing_activity': 'financing_cash_flow',
        'net_cash_flow': 'net_cash_flow',
        'other_asset': 'other_assets'
    }
    df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})

    # 4. Compute Metrics
    df = compute_metrics(df)
    
    # 5. Save cleaned data
    df.to_csv(output_path, index=False)
    print(f"Successfully processed: {file_name} -> {output_name}")

def main():
    base_path = Path(__file__).parent.parent
    raw_dir = base_path / 'data' / 'raw'
    clean_dir = base_path / 'data' / 'clean'
    
    clean_dir.mkdir(parents=True, exist_ok=True)
    
    # Mapping raw files to their cleaned counterparts as expected by the load script
    file_mapping = {
        'analysis.csv': 'fact_analysis.csv',
        'balancesheet.csv': 'fact_balance_sheet.csv',
        'cashflow.csv': 'fact_cash_flow.csv',
        'profitandloss.csv': 'fact_profit_loss.csv',
        'prosandcons.csv': 'fact_pros_cons.csv',
        'companies.csv': 'companies.csv',
        'documents.csv': 'documents.csv'
    }
    
    for raw_name, clean_name in file_mapping.items():
        process_file(raw_name, clean_name, raw_dir, clean_dir)
        
    # Generate dimension tables
    generate_dim_sector(clean_dir)
    generate_dim_company(clean_dir)
    generate_dim_year(clean_dir)

if __name__ == "__main__":
    main()
