# file: etl/01_extract_from_sql.py
import os
import pandas as pd
import re
import csv
from utils.logger import setup_logger

logger = setup_logger('extract')

def extract_tables_from_sql(sql_file_path):
    """
    Parses a MySQL/MariaDB dump file and extracts data into CSVs.
    """
    if not os.path.exists(sql_file_path):
        logger.error(f"SQL file not found at {sql_file_path}")
        return

    table_data = {
        'companies': [],
        'analysis': [],
        'balancesheet': [],
        'profitandloss': [],
        'cashflow': [],
        'prosandcons': [],
        'documents': []
    }

    current_table = None
    
    logger.info(f"Starting extraction from {sql_file_path}")
    
    with open(sql_file_path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            # Identify which table the INSERT statement belongs to
            table_match = re.search(r"INSERT INTO `(\w+)` VALUES", line)
            if table_match:
                current_table = table_match.group(1)
                
                if current_table in table_data:
                    # Extract the values part
                    values_part = line[line.find("VALUES") + 7:].strip()
                    # Basic parsing of (val1, val2), (val3, val4)
                    # This uses a regex to find content between balanced parentheses
                    rows = re.findall(r"\((.*?)\)(?:,|$|;)", values_part)
                    
                    for row in rows:
                        # Split by comma but ignore commas inside single quotes
                        # Simple csv parser can handle this if we treat ' as quotechar
                        reader = csv.reader([row], quotechar="'", skipinitialspace=True)
                        for val_list in reader:
                            # Replace NULL with empty string for pandas
                            clean_vals = [v if v != 'NULL' else '' for v in val_list]
                            table_data[current_table].append(clean_vals)

    # Save to CSV
    os.makedirs('data/raw', exist_ok=True)
    for table_name, data in table_data.items():
        if data:
            df = pd.DataFrame(data)
            output_path = f'data/raw/{table_name}.csv'
            df.to_csv(output_path, index=False)
            logger.info(f"Extracted {len(df)} rows for {table_name} -> {output_path}")
        else:
            logger.warning(f"No data found for table: {table_name}")

if __name__ == "__main__":
    # Assuming dump.sql is the source file
    extract_tables_from_sql('data/dump.sql')
