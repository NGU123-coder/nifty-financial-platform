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

                # 5. Seed ML Scores and ProfitLoss for 2022, 2023, 2024
                companies_stats = [
                    # Symbol, 2024_rev, 2024_profit, growth_rate
                    ('HDFCBANK', 150000, 45000, 0.15),
                    ('TCS', 240000, 46000, 0.12),
                    ('RELIANCE', 900000, 70000, 0.10),
                    ('INFY', 150000, 26000, 0.11),
                    ('TATAMOTORS', 400000, 31000, 0.20),
                    ('ICICIBANK', 120000, 33000, 0.18),
                    ('SBIN', 400000, 60000, 0.14),
                    ('AXISBANK', 100000, 24000, 0.16),
                    ('WIPRO', 90000, 11000, 0.08),
                    ('LT', 200000, 23000, 0.13),
                ]

                health_sequence = ['GOOD', 'EXCELLENT', 'EXCELLENT'] # 2022, 2023, 2024
                
                for symbol, rev_24, profit_24, growth in companies_stats:
                    comp = company_objs[symbol]
                    
                    for i, year_val in enumerate([2022, 2023, 2024]):
                        y_obj = year_objs[year_val]
                        
                        # Calculate back-dated revenue and profit
                        # rev_24 = rev_22 * (1+growth)^2
                        years_back = 2024 - year_val
                        rev = rev_24 / ((1 + growth) ** years_back)
                        profit = profit_24 / ((1 + growth) ** years_back)
                        
                        # ML Score
                        h_label = health_objs['EXCELLENT' if profit/rev > 0.2 else 'GOOD']
                        if year_val == 2024:
                             # For 2024, use specific labels to match original demo better
                             if symbol in ['HDFCBANK', 'TCS', 'ICICIBANK']: h_label = health_objs['EXCELLENT']
                             elif symbol in ['TATAMOTORS', 'WIPRO']: h_label = health_objs['AVERAGE']
                             else: h_label = health_objs['GOOD']

                        ms_obj, ms_created = MLScore.objects.get_or_create(
                            company=comp,
                            year=y_obj,
                            defaults={
                                'health': h_label,
                                'probability_score': 0.7 + (profit/rev) + (year_val-2022)*0.05
                            }
                        )
                        
                        # Profit Loss
                        pl_obj, pl_created = ProfitLoss.objects.get_or_create(
                            company=comp,
                            year=y_obj,
                            defaults={
                                'revenue': rev,
                                'net_profit': profit,
                                'net_profit_margin_pct': (profit/rev)*100 if rev > 0 else 0
                            }
                        )
                        if pl_created:
                            self.stdout.write(f"  + Created {year_val} ProfitLoss for {symbol}")

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
