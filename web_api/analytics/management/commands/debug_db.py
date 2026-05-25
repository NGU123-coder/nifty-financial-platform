from django.core.management.base import BaseCommand
from django.db import connection
from django.apps import apps
from analytics.models import Company, Sector, FiscalYear, MLScore, ProfitLoss

class Command(BaseCommand):
    help = 'Debugs the database state by listing tables and row counts'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('--- STARTING DATABASE DEBUG ---'))
        
        # 1. Active Database Engine
        engine = connection.settings_dict.get('ENGINE')
        host = connection.settings_dict.get('HOST')
        self.stdout.write(f"Active Database Engine: {engine}")
        self.stdout.write(f"Database Host: {host}")

        # 2. Migration Status for Analytics
        from django.db.migrations.recorder import MigrationRecorder
        applied_migrations = MigrationRecorder.Migration.objects.filter(app='analytics').values_list('name', flat=True)
        self.stdout.write(f"\nApplied Analytics Migrations: {list(applied_migrations)}")

        # 3. List all tables
        with connection.cursor() as cursor:
            if connection.vendor == 'postgresql':
                cursor.execute("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public'
                    ORDER BY table_name;
                """)
            elif connection.vendor == 'sqlite':
                cursor.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' 
                    ORDER BY name;
                """)
            else:
                self.stdout.write(f"Skipping table list for vendor: {connection.vendor}")
                tables = []
            
            if connection.vendor in ['postgresql', 'sqlite']:
                tables = cursor.fetchall()
                self.stdout.write(f"\nTotal Tables found: {len(tables)}")
                for table in tables:
                    self.stdout.write(f"  - {table[0]}")

        # 4. Check row counts for analytics models
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
