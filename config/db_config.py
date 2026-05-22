import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file, but do not override existing ones
load_dotenv(override=False)

# Base Directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Data Directories
DATA_DIR = BASE_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
CLEAN_DATA_DIR = DATA_DIR / "clean"

# Create directories if they don't exist
RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
CLEAN_DATA_DIR.mkdir(parents=True, exist_ok=True)

# Database Configuration
DB_NAME = os.getenv('DB_NAME', 'nifty_db')
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'postgres')
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')

DATABASE_URL = os.getenv("DATABASE_URL")

# If DATABASE_URL is not set, construct it from individual variables
if not DATABASE_URL:
    DATABASE_URL = f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Extract connection parameters for psycopg2
# Expected format: postgresql://user:password@host:port/dbname
import re
match = re.match(r'postgresql(\+psycopg2)?://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)', DATABASE_URL)
if match:
    DB_PARAMS = {
        'user': match.group(2),
        'password': match.group(3),
        'host': match.group(4),
        'port': match.group(5),
        'dbname': match.group(6)
    }
else:
    # Fallback to individual variables if regex fails
    DB_PARAMS = {
        'user': DB_USER,
        'password': DB_PASSWORD,
        'host': DB_HOST,
        'port': DB_PORT,
        'dbname': DB_NAME
    }