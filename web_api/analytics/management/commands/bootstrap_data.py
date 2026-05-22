import os
import pandas as pd
from django.core.management.base import BaseCommand
from django.db import connection
from analytics.models import Sector, HealthLabel, Company, FiscalYear
from django.conf import settings

class Command(BaseCommand):
    help = 'Bootstrap production database with initial dimension data'

    def handle(self, *args, **options):
        self.stdout.write('Starting production bootstrap...')
        
        # 1. Seed Health Labels
        labels = ['EXCELLENT', 'GOOD', 'AVERAGE', 'POOR', 'CRITICAL']
        for label in labels:
            HealthLabel.objects.get_or_create(label_name=label)
        self.stdout.write(self.style.SUCCESS('Health labels seeded.'))

        # 2. Seed Basic Sectors if empty
        sectors = ['Technology', 'Financial Services', 'Automobile', 'Energy', 'Consumer Goods']
        for s_name in sectors:
            Sector.objects.get_or_create(sector_name=s_name)
        self.stdout.write(self.style.SUCCESS('Basic sectors seeded.'))

        # 3. Try to load companies from local CSV if it exists
        csv_path = os.path.join(settings.BASE_DIR, '..', 'data', 'clean', 'dim_company.csv')
        if os.path.exists(csv_path):
            self.stdout.write(f'Loading companies from {csv_path}...')
            df = pd.read_csv(csv_path)
            tech_sector = Sector.objects.get(sector_name='Technology')
            for _, row in df.head(10).iterrows(): # Load first 10 for demo
                Company.objects.get_or_create(
                    symbol=row['symbol'],
                    defaults={
                        'company_name': row['company_name'],
                        'sector': tech_sector
                    }
                )
            self.stdout.write(self.style.SUCCESS('Initial companies seeded.'))
        else:
            self.stdout.write(self.style.WARNING('No company CSV found. Skipping company seeding.'))

        self.stdout.write(self.style.SUCCESS('Bootstrap complete.'))
