import os
from django.core.management.base import BaseCommand
from django.db import transaction
from analytics.models import Sector, Company, FiscalYear, HealthLabel, MLScore, ProfitLoss

class Command(BaseCommand):
    help = 'Seeds the database with initial demo data using ORM only'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('BOOTSTRAP STARTED'))
        
        try:
            with transaction.atomic():
                # 1. Seed Sectors
                sectors_data = ['Banking', 'IT', 'Automobile', 'Energy', 'Consumer Goods', 'Infrastructure']
                sector_objs = {}
                for name in sectors_data:
                    obj, created = Sector.objects.get_or_create(sector_name=name)
                    sector_objs[name] = obj
                    if created:
                        self.stdout.write(f"  + Created Sector: {name}")

                # 2. Seed Health Labels
                labels = ['EXCELLENT', 'GOOD', 'AVERAGE', 'POOR', 'CRITICAL']
                health_objs = {}
                for label in labels:
                    obj, created = HealthLabel.objects.get_or_create(label_name=label)
                    health_objs[label] = obj
                    if created:
                        self.stdout.write(f"  + Created Health Label: {label}")

                # 3. Seed Fiscal Years
                years_data = [
                    (2022, 'Mar 2022', 2022),
                    (2023, 'Mar 2023', 2023),
                    (2024, 'Mar 2024', 2024),
                ]
                year_objs = {}
                for fy, period, sort in years_data:
                    obj, created = FiscalYear.objects.get_or_create(
                        fiscal_year=fy, 
                        period_name=period,
                        defaults={'sort_order': sort}
                    )
                    year_objs[fy] = obj
                    if created:
                        self.stdout.write(f"  + Created Fiscal Year: {period}")

                # 4. Seed Companies
                companies_data = [
                    ('TCS', 'Tata Consultancy Services', 'IT'),
                    ('INFY', 'Infosys Ltd', 'IT'),
                    ('RELIANCE', 'Reliance Industries Ltd', 'Energy'),
                    ('HDFCBANK', 'HDFC Bank Ltd', 'Banking'),
                    ('ICICIBANK', 'ICICI Bank Ltd', 'Banking'),
                    ('TATAMOTORS', 'Tata Motors Ltd', 'Automobile'),
                    ('LT', 'Larsen & Toubro Ltd', 'Infrastructure'),
                    ('SBIN', 'State Bank of India', 'Banking'),
                    ('AXISBANK', 'Axis Bank Ltd', 'Banking'),
                    ('WIPRO', 'Wipro Ltd', 'IT'),
                ]
                
                company_objs = {}
                for symbol, name, s_name in companies_data:
                    obj, created = Company.objects.get_or_create(
                        symbol=symbol,
                        defaults={
                            'company_name': name,
                            'sector': sector_objs[s_name],
                            'industry': s_name
                        }
                    )
                    company_objs[symbol] = obj
                    if created:
                        self.stdout.write(f"  + Created Company: {symbol}")

                # 5. Seed ML Scores and ProfitLoss for 2024
                scores_2024 = [
                    ('HDFCBANK', 'EXCELLENT', 0.9250, 150000, 45000),
                    ('TCS', 'EXCELLENT', 0.9410, 240000, 46000),
                    ('RELIANCE', 'GOOD', 0.8250, 900000, 70000),
                    ('INFY', 'GOOD', 0.8120, 150000, 26000),
                    ('TATAMOTORS', 'AVERAGE', 0.6540, 400000, 31000),
                    ('ICICIBANK', 'EXCELLENT', 0.8950, 120000, 33000),
                    ('SBIN', 'GOOD', 0.7820, 400000, 60000),
                    ('AXISBANK', 'GOOD', 0.7650, 100000, 24000),
                    ('WIPRO', 'AVERAGE', 0.6120, 90000, 11000),
                    ('LT', 'GOOD', 0.7950, 200000, 23000),
                ]

                y2024 = year_objs[2024]
                for symbol, health_label, score, rev, profit in scores_2024:
                    comp = company_objs[symbol]
                    h_label = health_objs[health_label]
                    
                    # ML Score
                    ms_obj, ms_created = MLScore.objects.get_or_create(
                        company=comp,
                        year=y2024,
                        defaults={
                            'health': h_label,
                            'probability_score': score
                        }
                    )
                    if ms_created:
                        self.stdout.write(f"  + Created MLScore for {symbol}")
                    
                    # Profit Loss
                    pl_obj, pl_created = ProfitLoss.objects.get_or_create(
                        company=comp,
                        year=y2024,
                        defaults={
                            'revenue': rev,
                            'net_profit': profit,
                            'net_profit_margin_pct': (profit/rev)*100 if rev > 0 else 0
                        }
                    )
                    if pl_created:
                        self.stdout.write(f"  + Created ProfitLoss for {symbol}")

            self.stdout.write(self.style.SUCCESS('BOOTSTRAP COMPLETE'))
            
            # Final counts for verification
            self.stdout.write(f"TOTAL SECTORS: {Sector.objects.count()}")
            self.stdout.write(f"TOTAL COMPANIES: {Company.objects.count()}")
            self.stdout.write(f"TOTAL YEARS: {FiscalYear.objects.count()}")
            self.stdout.write(f"TOTAL SCORES: {MLScore.objects.count()}")
            self.stdout.write(f"TOTAL PL RECORDS: {ProfitLoss.objects.count()}")

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'BOOTSTRAP FAILED: {e}'))
            raise e
