import os
import pandas as pd
import numpy as np
import logging
from sqlalchemy import create_engine, text
from sklearn.preprocessing import MinMaxScaler
from config.db_config import DATABASE_URL
from utils.logger import setup_logger

# Initialize Logger
logger = setup_logger('financial_scoring_engine')

class FinancialScoringEngine:
    def __init__(self, db_url=None):
        """
        Initializes the scoring engine with a database URL.
        If db_url is not provided, it attempts to fetch it from the environment.
        """
        if not db_url:
            from config.db_config import DATABASE_URL
            db_url = DATABASE_URL
        
        if not db_url:
            raise ValueError("Database URL must be provided or set in environment (DATABASE_URL).")
            
        logger.info(f"Initializing FinancialScoringEngine with database.")
        try:
            self.engine = create_engine(db_url)
            # Test connection
            with self.engine.connect() as conn:
                pass
        except Exception as e:
            logger.error(f"Failed to create SQLAlchemy engine: {e}")
            raise

        self.scaler = MinMaxScaler()
        self.weights = {
            'profitability': 0.25,
            'growth': 0.20,
            'debt_stability': 0.15,
            'cash_flow': 0.15,
            'dividend': 0.10,
            'trend': 0.15
        }

    def fetch_data(self):
        """Fetches comprehensive financial data for all companies and years."""
        logger.info("Fetching data from warehouse...")
        query = """
        SELECT 
            dc.company_id, dc.symbol, dc.company_name, COALESCE(ds.sector_name, 'Unknown') as sector_name, dy.year_id, dy.fiscal_year,
            pl.revenue, pl.net_profit, pl.operating_profit, pl.dividend_payout_pct,
            bs.total_assets, bs.borrowings, (bs.equity_capital + bs.reserves) as total_equity,
            cf.operating_cash_flow, cf.free_cash_flow,
            an.market_cap, an.roce_pct, an.roe_pct, an.interest_coverage, an.dividend_yield
        FROM fact_profit_loss pl
        JOIN dim_company dc ON pl.company_id = dc.company_id
        LEFT JOIN dim_sector ds ON dc.sector_id = ds.sector_id
        JOIN dim_year dy ON pl.year_id = dy.year_id
        JOIN fact_balance_sheet bs ON pl.company_id = bs.company_id AND pl.year_id = bs.year_id
        JOIN fact_cash_flow cf ON pl.company_id = cf.company_id AND pl.year_id = cf.year_id
        JOIN fact_analysis an ON pl.company_id = an.company_id AND pl.year_id = an.year_id
        ORDER BY dc.symbol, dy.fiscal_year
        """
        return pd.read_sql(query, self.engine)

    def engineer_features(self, df):
        """Calculates key financial ratios and growth metrics."""
        logger.info("Engineering features...")
        
        # Sort for time-series calculations
        df = df.sort_values(['symbol', 'fiscal_year'])

        # 1. Profitability
        df['net_margin'] = np.where(df['revenue'] == 0, 0, df['net_profit'] / df['revenue'])
        
        # 2. Growth (YoY)
        df['rev_growth'] = df.groupby('symbol')['revenue'].pct_change().fillna(0)
        df['profit_growth'] = df.groupby('symbol')['net_profit'].pct_change().fillna(0)

        # 3. Debt & Stability
        df['debt_to_equity'] = np.where(df['total_equity'] == 0, 0, df['borrowings'] / df['total_equity'])
        df['interest_coverage_ratio'] = df['interest_coverage'].fillna(0)

        # 4. Cash Flow
        df['cash_to_profit'] = np.where(df['net_profit'] <= 0, 0, df['operating_cash_flow'] / df['net_profit'])

        # 5. Trend Scoring (Average growth over last 2 records)
        df['trend_score_raw'] = df.groupby('symbol')['profit_growth'].transform(lambda x: x.rolling(window=2, min_periods=1).mean())

        # Handle infinite values
        df = df.replace([np.inf, -np.inf], 0).fillna(0)
        return df

    def calculate_scores(self, df):
        """Applies sector-aware normalization and calculates final weighted scores."""
        logger.info("Calculating weighted scores with sector-aware ranking...")
        
        # Define pillars
        pillars = {
            'profitability': ['roe_pct', 'roce_pct', 'net_margin'],
            'growth': ['rev_growth', 'profit_growth'],
            'debt_stability': ['interest_coverage_ratio'], # Debt to equity is handled separately (inverted)
            'cash_flow': ['cash_to_profit'],
            'dividend': ['dividend_payout_pct', 'dividend_yield'],
            'trend': ['trend_score_raw']
        }

        # Sector-aware ranking and normalization
        for pillar, cols in pillars.items():
            pillar_scores = []
            for col in cols:
                # Rank within sector
                rank_col = f"{col}_rank"
                df[rank_col] = df.groupby(['sector_name', 'year_id'])[col].rank(pct=True)
                pillar_scores.append(df[rank_col])
            
            # Special case for debt_to_equity: Lower is better, so invert rank
            if pillar == 'debt_stability':
                df['d2e_rank'] = 1 - df.groupby(['sector_name', 'year_id'])['debt_to_equity'].rank(pct=True)
                pillar_scores.append(df['d2e_rank'])

            df[f"{pillar}_score"] = sum(pillar_scores) / len(pillar_scores)

        # Final Weighted Score
        df['probability_score'] = (
            df['profitability_score'] * self.weights['profitability'] +
            df['growth_score'] * self.weights['growth'] +
            df['debt_stability_score'] * self.weights['debt_stability'] +
            df['cash_flow_score'] * self.weights['cash_flow'] +
            df['dividend_score'] * self.weights['dividend'] +
            df['trend_score_raw'].clip(0, 1) * self.weights['trend']
        )

        # Scale final score to 0-1
        df['probability_score'] = self.scaler.fit_transform(df[['probability_score']])

        # Assign Labels
        def assign_label(score):
            if score >= 0.8: return 'EXCELLENT'
            if score >= 0.6: return 'GOOD'
            if score >= 0.4: return 'AVERAGE'
            return 'WEAK'

        df['health_label'] = df['probability_score'].apply(assign_label)
        return df

    def generate_insights(self, df):
        """Generates Pros and Cons for each company based on its metrics."""
        logger.info("Generating Pros and Cons...")
        insights = []

        for idx, row in df.iterrows():
            # Pros
            if row['roce_pct'] > 20: insights.append({'company_id': row['company_id'], 'type': 'PROS', 'point': 'Strong Return on Capital (ROCE > 20%)'})
            if row['debt_to_equity'] < 0.5: insights.append({'company_id': row['company_id'], 'type': 'PROS', 'point': 'Low Debt to Equity ratio'})
            if row['cash_to_profit'] > 1: insights.append({'company_id': row['company_id'], 'type': 'PROS', 'point': 'Excellent cash conversion from profits'})
            if row['dividend_yield'] > 3: insights.append({'company_id': row['company_id'], 'type': 'PROS', 'point': 'High dividend yield (> 3%)'})
            
            # Cons
            if row['debt_to_equity'] > 2: insights.append({'company_id': row['company_id'], 'type': 'CONS', 'point': 'High Debt levels (D/E > 2)'})
            if row['net_margin'] < 0.05: insights.append({'company_id': row['company_id'], 'type': 'CONS', 'point': 'Thin net profit margins (< 5%)'})
            if row['interest_coverage_ratio'] < 2: insights.append({'company_id': row['company_id'], 'type': 'CONS', 'point': 'Weak interest coverage'})
            if row['rev_growth'] < -0.1: insights.append({'company_id': row['company_id'], 'type': 'CONS', 'point': 'Significant revenue decline (> 10%)'})

        return pd.DataFrame(insights)

    def save_results(self, df, insights):
        """Saves scores and insights to the database."""
        logger.info("Saving results to database...")
        
        with self.engine.begin() as conn:
            # 1. Update dim_health_label
            labels = ['EXCELLENT', 'GOOD', 'AVERAGE', 'WEAK']
            for lbl in labels:
                conn.execute(text("INSERT INTO dim_health_label (label_name) VALUES (:l) ON CONFLICT DO NOTHING"), {"l": lbl})
            
            label_map = dict(conn.execute(text("SELECT label_name, health_id FROM dim_health_label")).fetchall())
            df['health_id'] = df['health_label'].map(label_map)

            # 2. Insert Scores
            for _, row in df.iterrows():
                conn.execute(text("""
                    INSERT INTO fact_ml_scores (company_id, year_id, health_id, probability_score)
                    VALUES (:cid, :yid, :hid, :score)
                    ON CONFLICT (company_id, year_id) DO UPDATE SET
                        health_id = EXCLUDED.health_id,
                        probability_score = EXCLUDED.probability_score,
                        prediction_date = CURRENT_TIMESTAMP
                """), {
                    "cid": int(row['company_id']),
                    "yid": int(row['year_id']),
                    "hid": int(row['health_id']),
                    "score": float(row['probability_score'])
                })

            # 3. Insert Pros/Cons (Clear existing for current analysis cycle)
            # In a real prod env, we might want to version these. Here we refresh.
            conn.execute(text("DELETE FROM fact_pros_cons"))
            for _, row in insights.iterrows():
                conn.execute(text("""
                    INSERT INTO fact_pros_cons (company_id, type, point)
                    VALUES (:cid, :type, :point)
                """), {
                    "cid": int(row['company_id']),
                    "type": row['type'],
                    "point": row['point']
                })

        logger.info("Database update successful.")

    def run_pipeline(self):
        """Executes the full ML pipeline."""
        try:
            raw_data = self.fetch_data()
            if raw_data.empty:
                logger.error("No data found in warehouse.")
                return

            featured_data = self.engineer_features(raw_data)
            scored_data = self.calculate_scores(featured_data)
            insights = self.generate_insights(scored_data)
            
            self.save_results(scored_data, insights)
            
            logger.info("--- Pipeline Completed Successfully ---")
            logger.info(f"Processed {len(scored_data)} records and generated {len(insights)} insights.")
            
        except Exception as e:
            logger.error(f"Pipeline failed: {str(e)}", exc_info=True)

if __name__ == "__main__":
    if not DATABASE_URL:
        print("DATABASE_URL not set in .env")
    else:
        engine = FinancialScoringEngine(DATABASE_URL)
        engine.run_pipeline()
