import pandas as pd
import os
import numpy as np
from pathlib import Path

def detect_header_row(df):
    """
    Find the first row that likely contains headers.
    Heuristic: High number of non-null values and mostly strings.
    """
    for i, row in df.iterrows():
        # Count non-null values
        non_null_count = row.notna().sum()
        
        # Check if row has a reasonable number of values (at least 2)
        if non_null_count >= 2:
            # Check if values are mostly strings (meaningful names)
            string_values = [v for v in row.values if isinstance(v, str) and len(v.strip()) > 0]
            if len(string_values) / non_null_count > 0.5:
                return i
    return 0

def clean_column_names(df):
    """
    Clean column names: lowercase and replace spaces with underscores.
    """
    df.columns = [
        str(col).strip().lower().replace(' ', '_').replace('\n', '_') 
        for col in df.columns
    ]
    # Remove any columns that are still 'nan' or empty
    df = df.loc[:, ~df.columns.str.contains('^nan|^unnamed', na=False)]
    return df

def clean_data(df):
    """
    Clean data: strip whitespace from strings and replace 'NULL'/'Null' with NaN.
    Applied ONLY to object-type columns to avoid errors with numeric types.
    """
    # 1. Replace 'NULL' or 'Null' string variants with actual NaN
    df = df.replace(['NULL', 'Null', 'null', 'None', 'none'], np.nan)
    
    # 2. Apply string cleaning ONLY to object (string) columns
    for col in df.select_dtypes(include=['object']):
        # Convert to string, strip, and put back NaNs (which become 'nan' string)
        df[col] = df[col].astype(str).str.strip().replace(['nan', 'None'], np.nan)
    
    return df

def extract_and_clean():
    base_path = Path(__file__).parent.parent
    data_dir = base_path / 'data'
    output_dir = data_dir / 'raw'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    excel_files = [
        'analysis.xlsx',
        'balancesheet.xlsx',
        'cashflow.xlsx',
        'companies.xlsx',
        'documents.xlsx',
        'profitandloss.xlsx',
        'prosandcons.xlsx'
    ]
    
    for file_name in excel_files:
        input_path = data_dir / file_name
        output_path = output_dir / f"{Path(file_name).stem}.csv"
        
        if not input_path.exists():
            print(f"Warning: {file_name} not found. Skipping...")
            continue
            
        try:
            # 1. Read Excel WITHOUT header
            df_raw = pd.read_excel(input_path, header=None)
            
            # 2. Detect Header Row
            header_idx = detect_header_row(df_raw)
            
            # 3. Set header and slice data
            df = df_raw.iloc[header_idx + 1:].copy()
            df.columns = df_raw.iloc[header_idx]
            
            # 4. Drop fully empty rows and columns
            df = df.dropna(how='all').dropna(axis=1, how='all')
            
            # 5. Clean column names
            df = clean_column_names(df)
            
            # 6. Clean data
            df = clean_data(df)
            
            # 7. Final check: drop rows where key identifiers might be missing
            if not df.empty:
                df = df.dropna(subset=[df.columns[0]], how='all')
            
            # 8. Save as CSV
            df.to_csv(output_path, index=False)
            
            print("-" * 40)
            print(f"Filename: {file_name} (Header detected at row {header_idx + 1})")
            print(f"Rows:     {len(df)}")
            print(f"Columns:  {', '.join(df.columns.tolist()[:5])}...")
            
        except Exception as e:
            print(f"Error processing {file_name}: {e}")

if __name__ == "__main__":
    extract_and_clean()
