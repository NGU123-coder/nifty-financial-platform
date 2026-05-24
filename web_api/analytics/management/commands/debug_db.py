from django.core.management.base import BaseCommand
from django.db import connection
from analytics.models import Company, Sector, FiscalYear, MLScore, ProfitLoss

class Command(BaseCommand):
    help = 'Debugs the database state by listing tables and row counts'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('--- STARTING DATABASE DEBUG ---'))
        
        # 1. List all tables in public schema
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name;
            """)
            tables = cursor.fetchall()
            self.stdout.write("PostgreSQL Tables found:")
            for table in tables:
                self.stdout.write(f"  - {table[0]}")

        # 2. Check row counts for analytics models
        models = [
            ('Sector', Sector),
            ('Company', Company),
            ('FiscalYear', FiscalYear),
            ('MLScore', MLScore),
            ('ProfitLoss', ProfitLoss),
        ]
        
        self.stdout.write("\nModel Row Counts:")
        for name, model in models:
            try:
                count = model.objects.count()
                self.stdout.write(f"  - {name} ({model._meta.db_table}): {count}")
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  - {name}: ERROR - {e}"))

        self.stdout.write(self.style.SUCCESS('--- DATABASE DEBUG COMPLETED ---'))
