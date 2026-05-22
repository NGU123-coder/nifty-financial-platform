from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker
from config.db_config import DATABASE_URL
from typing import List, Dict, Any

app = FastAPI(
    title="Nifty Financial Platform API",
    description="Backend API for accessing financial company data and ML health scores",
    version="1.0.0"
)

# Database Setup
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/")
async def root():
    """Returns a simple welcome message."""
    return {"message": "Welcome to the Nifty Financial Platform API", "status": "online"}

@app.get("/companies")
async def get_companies(db: Session = Depends(get_db)):
    """Returns company_id, name, and symbol."""
    query = text("SELECT company_id, company_name as name, symbol FROM dim_company ORDER BY symbol")
    result = db.execute(query)
    return [dict(row._mapping) for row in result]

@app.get("/scores")
async def get_scores(db: Session = Depends(get_db)):
    """Returns symbol, year_id, label_name, and probability_score."""
    query = text("""
        SELECT 
            dc.symbol, 
            f.year_id, 
            dh.label_name, 
            f.probability_score
        FROM fact_ml_scores f
        JOIN dim_company dc ON f.company_id = dc.company_id
        JOIN dim_health_label dh ON f.health_id = dh.health_id
        ORDER BY dc.symbol, f.year_id
    """)
    result = db.execute(query)
    return [dict(row._mapping) for row in result]

@app.get("/top-performing")
async def get_top_performing(db: Session = Depends(get_db)):
    """Returns top 10 companies by average probability_score."""
    query = text("""
        SELECT 
            dc.symbol, 
            dc.company_name, 
            AVG(f.probability_score) as average_score
        FROM fact_ml_scores f
        JOIN dim_company dc ON f.company_id = dc.company_id
        GROUP BY dc.symbol, dc.company_name
        ORDER BY average_score DESC
        LIMIT 10
    """)
    result = db.execute(query)
    return [dict(row._mapping) for row in result]

@app.get("/company/{symbol}")
async def get_company_timeseries(symbol: str, db: Session = Depends(get_db)):
    """Returns time-series data for a company."""
    query = text("""
        SELECT 
            dy.fiscal_year, 
            dy.period_name, 
            dh.label_name, 
            f.probability_score
        FROM fact_ml_scores f
        JOIN dim_company dc ON f.company_id = dc.company_id
        JOIN dim_year dy ON f.year_id = dy.year_id
        JOIN dim_health_label dh ON f.health_id = dh.health_id
        WHERE UPPER(dc.symbol) = UPPER(:symbol)
        ORDER BY dy.sort_order
    """)
    result = db.execute(query, {"symbol": symbol})
    data = [dict(row._mapping) for row in result]
    
    if not data:
        raise HTTPException(status_code=404, detail=f"Company '{symbol}' not found.")
        
    return {
        "symbol": symbol.upper(),
        "time_series": data
    }
