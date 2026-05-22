import os
import subprocess
import logging
import pandas as pd
import numpy as np
from celery import shared_task, chain
from django.conf import settings
from scoring.financial_scoring_engine import FinancialScoringEngine
from .models import Company, ProfitLoss, MLScore

logger = logging.getLogger(__name__)

# Base task parameters for consistency
TASK_PARAMS = {
    'bind': True,
    'max_retries': 3,
    'default_retry_delay': 300,
    'acks_late': True
}

@shared_task(**TASK_PARAMS)
def run_etl_pipeline(self):
    """Orchestrates the full ETL pipeline using the consolidated 03_load script."""
    task_id = self.request.id
    logger.info(f"[Task {task_id}] Starting ETL Pipeline automation...")
    try:
        # Define paths relative to BASE_DIR (/app/web_api)
        root_dir = os.path.join(settings.BASE_DIR, '..')
        etl_script = os.path.join(root_dir, 'etl', '03_load.py')
        
        logger.info(f"[Task {task_id}] Running consolidated ETL script: {etl_script}")
        result = subprocess.run(['python', etl_script], capture_output=True, text=True, check=True, cwd=root_dir)
        
        logger.info(f"[Task {task_id}] ETL Output: {result.stdout}")
        logger.info(f"[Task {task_id}] ETL Pipeline completed successfully.")
        return "ETL_SUCCESS"
    except subprocess.CalledProcessError as e:
        logger.error(f"[Task {task_id}] ETL Subprocess failed: {e.stderr}")
        raise self.retry(exc=e)
    except Exception as exc:
        logger.error(f"[Task {task_id}] ETL Pipeline failed: {exc}")
        raise self.retry(exc=exc)

@shared_task(**TASK_PARAMS)
def score_all_companies(self, prev_result=None):
    """Runs the Financial Health Scoring Engine."""
    task_id = self.request.id
    logger.info(f"[Task {task_id}] Starting ML Scoring Engine task (Previous: {prev_result})...")
    try:
        from config.db_config import DATABASE_URL
        if not DATABASE_URL:
            raise ValueError("DATABASE_URL not configured")
            
        engine = FinancialScoringEngine(DATABASE_URL)
        engine.run_pipeline()
        logger.info(f"[Task {task_id}] ML Scoring Engine task completed successfully.")
        return "SCORING_SUCCESS"
    except Exception as e:
        logger.error(f"[Task {task_id}] ML Scoring task failed: {e}", exc_info=True)
        raise self.retry(exc=e)

@shared_task(**TASK_PARAMS, ignore_result=True)
def detect_anomalies(self, prev_result=None):
    """ML task to identify financial anomalies using Isolation Forest."""
    task_id = self.request.id
    logger.info(f"[Task {task_id}] Starting Anomaly Detection task (Previous: {prev_result})...")
    try:
        from sklearn.ensemble import IsolationForest
        from .models import ProfitLoss
        
        # Use Django ORM to fetch only necessary fields
        data = ProfitLoss.objects.values('id', 'net_profit_margin_pct')
        df = pd.DataFrame(list(data))
        
        if df.empty:
            logger.warning(f"[Task {task_id}] No data for anomaly detection.")
            return "NO_DATA"
        
        X = df[['net_profit_margin_pct']].fillna(0)
        
        iso = IsolationForest(contamination=0.05)
        df['is_anomaly'] = iso.fit_predict(X)
        
        logger.info(f"[Task {task_id}] Anomaly Detection complete. Found {len(df[df['is_anomaly'] == -1])} anomalies.")
        return "ANOMALY_SUCCESS"
    except Exception as e:
        logger.error(f"[Task {task_id}] Anomaly Detection failed: {e}")
        raise self.retry(exc=e)

@shared_task
def run_full_maintenance_workflow():
    """
    Orchestrates the full maintenance workflow in order:
    ETL -> Scoring -> Anomalies
    """
    logger.info("Triggering full maintenance workflow chain...")
    workflow = chain(
        run_etl_pipeline.s(),
        score_all_companies.s(),
        detect_anomalies.s()
    )
    return workflow.apply_async()

@shared_task
def detect_trends():
    """Analyzes multi-year trends for all companies."""
    logger.info("Starting Trend Analysis task...")
    # Trend analysis logic from notebooks
    return "Trend Analysis Success"
