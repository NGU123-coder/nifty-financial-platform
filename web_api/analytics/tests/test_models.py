from django.test import TestCase
from analytics.models import Sector, Company, FiscalYear, HealthLabel

class ModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        # We need to bypass 'managed = False' for testing if possible, 
        # but Django 4.0+ handles this better in migrations or by using a custom runner.
        # For simplicity in this environment, we'll assume the test DB setup works or we mock.
        pass

    def test_sector_str(self):
        sector = Sector(sector_name="Technology")
        self.assertEqual(str(sector), "Technology")

    def test_health_label_str(self):
        label = HealthLabel(label_name="EXCELLENT")
        self.assertEqual(str(label), "EXCELLENT")

    def test_company_str(self):
        sector = Sector(sector_name="Finance")
        company = Company(symbol="RELIANCE", company_name="Reliance Industries", sector=sector)
        self.assertEqual(str(company), "RELIANCE - Reliance Industries")

    def test_fiscal_year_str(self):
        year = FiscalYear(fiscal_year=2024, period_name="Mar 2024")
        self.assertEqual(str(year), "Mar 2024")
