import os
import random
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import connection
from analytics.models import Sector, HealthLabel, Company, FiscalYear, ProfitLoss, MLScore
from django.conf import settings

class Command(BaseCommand):
    help = 'Bootstrap production database with dimension and sample fact data'

    def handle(self, *args, **options):
        self.stdout.write('Starting comprehensive production bootstrap...')
        
        # 1. Seed Health Labels
        labels = ['EXCELLENT', 'GOOD', 'AVERAGE', 'POOR', 'CRITICAL']
        health_objs = {}
        for label in labels:
            obj, _ = HealthLabel.objects.get_or_create(label_name=label)
            health_objs[label] = obj
        self.stdout.write(self.style.SUCCESS('Health labels initialized.'))

        # 2. Seed Sectors
        sectors = ['Technology', 'Financial Services', 'Automobile', 'Energy', 'Consumer Goods']
        sector_objs = {}
        for s_name in sectors:
            obj, _ = Sector.objects.get_or_create(sector_name=s_name)
            sector_objs[s_name] = obj
        self.stdout.write(self.style.SUCCESS('Sectors initialized.'))

        # 3. Seed Years
        year_objs = {}
        for yr in [2021, 2022, 2023, 2024]:
            obj, _ = FiscalYear.objects.get_or_create(
                fiscal_year=yr, 
                period_name=f'Mar {yr}',
                defaults={'sort_order': yr}
            )
            year_objs[yr] = obj
        self.stdout.write(self.style.SUCCESS('Fiscal years initialized.'))

        # 4. Seed Sample Companies
        demo_companies = [
            ('TCS', 'Tata Consultancy Services', 'Technology'),
            ('RELIANCE', 'Reliance Industries Ltd', 'Energy'),
            ('HDFCBANK', 'HDFC Bank Ltd', 'Financial Services'),
            ('TATAMOTORS', 'Tata Motors Ltd', 'Automobile'),
            ('HINDUNILVR', 'Hindustan Unilever Ltd', 'Consumer Goods'),
            ('INFY', 'Infosys Ltd', 'Technology'),
            ('ICICIBANK', 'ICICI Bank Ltd', 'Financial Services'),
            ('SBIN', 'State Bank of India', 'Financial Services'),
            ('BHARTIARTL', 'Bharti Airtel Ltd', 'Technology'),
            ('ITC', 'ITC Ltd', 'Consumer Goods'),
        ]

        companies = []
        for sym, name, sec in demo_companies:
            comp, created = Company.objects.get_or_create(
                symbol=sym,
                defaults={
                    'company_name': name,
                    'sector': sector_objs[sec]
                }
            )
            companies.append(comp)
        self.stdout.write(self.style.SUCCESS(f'Seeded {len(companies)} core Nifty companies.'))

        # 5. Seed Sample Fact Data (P&L and ML Scores)
        self.stdout.write('Seeding sample P&L and ML scores for dashboard...')
        for comp in companies:
            for yr_val, yr_obj in year_objs.items():
                # Random financial data for demo
                rev = Decimal(random.randint(5000, 50000))
                profit = rev * Decimal(random.uniform(0.05, 0.25))
                
                ProfitLoss.objects.get_or_create(
                    company=comp,
                    year=yr_obj,
                    defaults={
                        'revenue': rev,
                        'net_profit': profit,
                        'net_profit_margin_pct': (profit / rev) * 100
                    }
                )

                # ML Scores (only for the latest year for dashboard display)
                if yr_val == 2024:
                    prob = Decimal(random.uniform(0.4, 0.95))
                    label = 'AVERAGE'
                    if prob > 0.8: label = 'EXCELLENT'
                    elif prob > 0.7: label = 'GOOD'
                    elif prob < 0.5: label = 'POOR'

                    MLScore.objects.get_or_create(
                        company=comp,
                        year=yr_obj,
                        defaults={
                            'health': health_objs[label],
                            'probability_score': prob
                        }
                    )

        self.stdout.write(self.style.SUCCESS('Successfully seeded warehouse fact data for dashboard visualization.'))
        self.stdout.write(self.style.SUCCESS('BOOTSTRAP COMPLETE - Production database is ready.'))
