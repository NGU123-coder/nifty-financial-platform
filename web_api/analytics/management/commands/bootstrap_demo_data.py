import random
from decimal import Decimal
from django.core.management.base import BaseCommand
from analytics.models import Sector, HealthLabel, Company, FiscalYear, ProfitLoss, MLScore

class Command(BaseCommand):
    help = 'Seeds production database with robust demo data for visual confirmation'

    def handle(self, *args, **options):
        self.stdout.write('--- STARTING DEMO DATA BOOTSTRAP ---')
        
        # 1. Health Labels
        labels = ['EXCELLENT', 'GOOD', 'AVERAGE', 'POOR', 'CRITICAL']
        h_objs = {}
        for l in labels:
            obj, _ = HealthLabel.objects.get_or_create(label_name=l)
            h_objs[l] = obj
        
        # 2. Sectors
        secs = ['Technology', 'Financial Services', 'Automobile', 'Energy', 'Consumer Goods']
        s_objs = {}
        for s in secs:
            obj, _ = Sector.objects.get_or_create(sector_name=s)
            s_objs[s] = obj

        # 3. Years
        y_objs = {}
        for y in [2022, 2023, 2024]:
            obj, _ = FiscalYear.objects.get_or_create(
                fiscal_year=y, 
                period_name=f'Mar {y}',
                defaults={'sort_order': y}
            )
            y_objs[y] = obj

        # 4. Companies
        demo = [
            ('RELIANCE', 'Reliance Industries', 'Energy'),
            ('TCS', 'Tata Consultancy Services', 'Technology'),
            ('HDFCBANK', 'HDFC Bank', 'Financial Services'),
            ('INFY', 'Infosys Ltd', 'Technology'),
            ('ICICIBANK', 'ICICI Bank', 'Financial Services'),
            ('TATAMOTORS', 'Tata Motors', 'Automobile'),
            ('SBIN', 'State Bank of India', 'Financial Services'),
            ('BHARTIARTL', 'Bharti Airtel', 'Technology'),
            ('ITC', 'ITC Ltd', 'Consumer Goods'),
            ('HINDUNILVR', 'Hindustan Unilever', 'Consumer Goods'),
        ]

        for sym, name, sec in demo:
            comp, _ = Company.objects.get_or_create(
                symbol=sym,
                defaults={'company_name': name, 'sector': s_objs[sec]}
            )
            
            # Seed P&L and ML Scores
            for yr_val, yr_obj in y_objs.items():
                rev = Decimal(random.randint(10000, 100000))
                prof = rev * Decimal(random.uniform(0.05, 0.20))
                ProfitLoss.objects.get_or_create(
                    company=comp, year=yr_obj,
                    defaults={
                        'revenue': rev, 'net_profit': prof,
                        'net_profit_margin_pct': (prof/rev)*100
                    }
                )
                
                if yr_val == 2024:
                    prob = Decimal(random.uniform(0.4, 0.95))
                    lbl = 'AVERAGE'
                    if prob > 0.85: lbl = 'EXCELLENT'
                    elif prob > 0.70: lbl = 'GOOD'
                    elif prob < 0.50: lbl = 'POOR'
                    
                    MLScore.objects.get_or_create(
                        company=comp, year=yr_obj,
                        defaults={'health': h_objs[lbl], 'probability_score': prob}
                    )

        self.stdout.write(self.style.SUCCESS('--- DEMO BOOTSTRAP COMPLETE ---'))
