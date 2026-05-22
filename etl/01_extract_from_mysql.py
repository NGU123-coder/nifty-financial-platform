import re
import pandas as pd
import logging
from pathlib import Path
import sys
import os
import shutil

# Add parent directory to path to import config and utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.db_config import RAW_DATA_DIR, DATA_DIR
from utils.logger import setup_logger

logger = setup_logger("01_extract_sql")

def ensure_directories():
    """Ensures necessary data directories exist."""
    for directory in [DATA_DIR, RAW_DATA_DIR]:
        if not directory.exists():
            directory.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created missing directory: {directory}")

def auto_detect_sql_dump():
    """
    Searches for any .sql file in the project if the default dump.sql is missing.
    Relocates the first found candidate to data/raw/dump.sql.
    """
    default_path = RAW_DATA_DIR / "dump.sql"
    
    if default_path.exists():
        return default_path
    
    logger.info("Default dump.sql not found. Searching project for alternative SQL files...")
    
    # Search for all .sql files in the project root and subdirectories
    project_root = Path(__file__).resolve().parent.parent
    sql_files = list(project_root.rglob("*.sql"))
    
    # Filter out schema files or known non-data files
    candidates = [f for f in sql_files if f.name.lower() != "schema.sql" and "migrations" not in str(f)]
    
    if candidates:
        # Sort by size to pick the most likely data dump (usually the largest)
        candidates.sort(key=lambda x: x.stat().st_size, reverse=True)
        best_candidate = candidates[0]
        
        logger.info(f"Auto-detected SQL candidate: {best_candidate} ({best_candidate.stat().st_size / 1024:.2f} KB)")
        
        try:
            shutil.copy(best_candidate, default_path)
            logger.info(f"Relocated {best_candidate.name} to {default_path} successfully.")
            return default_path
        except Exception as e:
            logger.error(f"Failed to relocate SQL file: {e}")
    
    return None

def parse_sql_insert(line):
    """
    Parses an INSERT INTO statement and returns table name and values.
    Handles escaped quotes and multiple rows in one insert.
    """
    # Regex to extract table name
    table_match = re.search(r"INSERT INTO `?(\w+)`?", line, re.IGNORECASE)
    if not table_match:
        return None, None
    
    table_name = table_match.group(1)
    
    # Extract values part
    try:
        values_index = line.upper().find("VALUES")
        if values_index == -1: return None, None
        values_part = line[values_index + 6:].strip()
    except Exception:
        return None, None
    
    rows = []
    # Match (...) but handle potential nested content
    pattern = re.compile(r"\((.*?)\)(?:,|$|;)", re.DOTALL)
    for match in pattern.finditer(values_part):
        row_str = match.group(1)
        # Split by comma but ignore commas inside single quotes
        # This regex is a bit more robust for standard SQL exports
        row_values = re.findall(r"(?:'((?:''|[^'])*)'|NULL|(-?\d+\.?\d*))", row_str)
        
        processed_row = []
        for v in row_values:
            if v[0]: # String match
                processed_row.append(v[0].replace("''", "'"))
            elif v[1]: # Number match
                processed_row.append(v[1])
            else: # NULL match
                processed_row.append(None)
        
        if processed_row:
            rows.append(processed_row)
    
    return table_name, rows

def extract_from_sql(dump_path=None):
    """
    Reads a SQL dump file and extracts data into CSVs.
    """
    ensure_directories()
    
    # 1. Handle provided path vs default vs auto-detect
    if dump_path:
        dump_path = Path(dump_path)
    else:
        dump_path = auto_detect_sql_dump()
        
    if not dump_path or not dump_path.exists():
        logger.error(f"CRITICAL: No valid SQL dump file found at {dump_path or 'any location'}. Extraction aborted.")
        return False

    logger.info(f">>> Starting Extraction Phase from: {dump_path}")
    
    table_data = {}
    
    try:
        with open(dump_path, 'r', encoding='utf-8', errors='ignore') as f:
            current_insert = ""
            for line in f:
                line = line.strip()
                if not line or line.startswith("--") or line.startswith("/*"): continue
                
                if line.upper().startswith("INSERT INTO"):
                    current_insert = line
                elif current_insert:
                    current_insert += " " + line
                
                if current_insert and current_insert.endswith(";"):
                    table_name, rows = parse_sql_insert(current_insert)
                    if table_name and rows:
                        if table_name not in table_data:
                            table_data[table_name] = []
                        table_data[table_name].extend(rows)
                    current_insert = ""

        # Export to CSV
        if not table_data:
            logger.warning("No INSERT statements found in the SQL dump.")
            return False

        for table_name, rows in table_data.items():
            df = pd.DataFrame(rows)
            output_file = RAW_DATA_DIR / f"{table_name.lower()}.csv"
            df.to_csv(output_file, index=False)
            logger.info(f"Successfully extracted {len(df)} rows for table: {table_name}")

        logger.info(f"Extraction complete. CSVs saved to {RAW_DATA_DIR}")
        return True

    except Exception as e:
        logger.error(f"An error occurred during SQL extraction: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    """
    Professional entry point for ETL extraction.
    Supports:
    1. python etl/01_extract_from_mysql.py (Auto-detect mode)
    2. python etl/01_extract_from_mysql.py "C:/path/to/data.sql" (Manual mode)
    """
    sql_path = sys.argv[1] if len(sys.argv) > 1 else None
    
    if extract_from_sql(sql_path):
        logger.info("ETL Extraction Process Finished Successfully.")
        sys.exit(0)
    else:
        logger.error("ETL Extraction Process Failed.")
        sys.exit(1)
