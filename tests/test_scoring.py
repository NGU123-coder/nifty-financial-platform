import unittest
from unittest.mock import MagicMock, patch
import pandas as pd
import numpy as np
import sys
import os

# Ensure project root is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scoring.financial_scoring_engine import FinancialScoringEngine

class TestScoringEngine(unittest.TestCase):
    @patch('scoring.financial_scoring_engine.create_engine')
    def setUp(self, mock_create_engine):
        self.engine = FinancialScoringEngine(db_url="postgresql://user:pass@localhost/db")

    def test_engineer_features(self):
        df = pd.DataFrame({
            'symbol': ['AAPL', 'AAPL'],
            'fiscal_year': [2023, 2024],
            'revenue': [100, 120],
            'net_profit': [10, 15],
            'total_equity': [50, 60],
            'borrowings': [10, 10],
            'interest_coverage': [5, 6],
            'operating_cash_flow': [20, 25]
        })
        featured_df = self.engine.engineer_features(df)
        self.assertAlmostEqual(featured_df.iloc[1]['rev_growth'], 0.2)
        self.assertAlmostEqual(featured_df.iloc[1]['net_margin'], 0.125)

    def test_calculate_scores_basic(self):
        df = pd.DataFrame({
            'company_id': [1, 2],
            'symbol': ['A', 'B'],
            'sector_name': ['Tech', 'Tech'],
            'year_id': [1, 1],
            'roe_pct': [20, 10],
            'roce_pct': [25, 15],
            'net_margin': [0.2, 0.1],
            'rev_growth': [0.1, 0.05],
            'profit_growth': [0.15, 0.05],
            'interest_coverage_ratio': [10, 5],
            'debt_to_equity': [0.1, 0.5],
            'cash_to_profit': [1.2, 0.8],
            'dividend_payout_pct': [30, 20],
            'dividend_yield': [2, 1],
            'trend_score_raw': [0.1, 0.05]
        })
        scored_df = self.engine.calculate_scores(df)
        self.assertIn('probability_score', scored_df.columns)
        self.assertIn('health_label', scored_df.columns)
        self.assertEqual(scored_df.iloc[0]['health_label'], 'EXCELLENT')

if __name__ == '__main__':
    unittest.main()
