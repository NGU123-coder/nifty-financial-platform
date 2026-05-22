from django.test import TestCase
from unittest.mock import patch
from analytics.tasks import run_etl_pipeline, score_all_companies

class TaskTests(TestCase):
    @patch('analytics.tasks.subprocess.run')
    def test_run_etl_pipeline(self, mock_run):
        run_etl_pipeline.delay()
        self.assertTrue(run_etl_pipeline.name.endswith('run_etl_pipeline'))

    @patch('analytics.tasks.FinancialScoringEngine')
    def test_score_all_companies(self, mock_engine):
        score_all_companies.delay()
        self.assertTrue(score_all_companies.name.endswith('score_all_companies'))
