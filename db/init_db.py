# file: db/init_db.py
from sqlalchemy import create_engine, text
from config.db_config import DATABASE_URL
import os
import logging

logger = logging.getLogger(__name__)

def init_db():
    schema_path = os.path.join(os.path.dirname(__file__), 'schema.sql')
    if not os.path.exists(schema_path):
        logger.error(f"Schema file not found at {schema_path}")
        return

    with open(schema_path, 'r') as f:
        sql = f.read()
    
    if not DATABASE_URL:
        logger.error("DATABASE_URL not set.")
        return

    engine = create_engine(DATABASE_URL)
    
    try:
        with engine.begin() as conn:
            # Execute the entire script as one block
            # Note: For some Postgres features, we might need to split, 
            # but standard CREATE TABLE works fine in one block.
            conn.execute(text(sql))
        logger.info("Database schema initialized successfully.")
    except Exception as e:
        logger.error(f"Error initializing schema: {e}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    init_db()
