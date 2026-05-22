import pandas as pd
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def extract_csv(file_path):
    """
    Reads a CSV file into a pandas DataFrame.
    """
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        return pd.DataFrame()
    
    try:
        df = pd.read_csv(file_path)
        logger.info(f"Extracted {len(df)} rows from {file_path}")
        return df
    except Exception as e:
        logger.error(f"Error reading {file_path}: {e}")
        return pd.DataFrame()

def run_extraction(raw_data_dir='data/raw/'):
    """
    Extracts all necessary CSV files for the ETL process.
    """
    files = {
        'profit_loss': 'profitandloss.csv',
        'balance_sheet': 'balancesheet.csv',
        'cash_flow': 'cashflow.csv',
        'analysis': 'analysis.csv',
        'companies': 'companies.csv'
    }
    
    extracted_data = {}
    for key, filename in files.items():
        path = os.path.join(raw_data_dir, filename)
        extracted_data[key] = extract_csv(path)
        
    return extracted_data

if __name__ == "__main__":
    data = run_extraction()
    for name, df in data.items():
        print(f"{name}: {len(df)} rows")
