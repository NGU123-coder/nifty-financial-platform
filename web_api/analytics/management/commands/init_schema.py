import os
import sys
from django.core.management.base import BaseCommand
from django.db import connection
from django.conf import settings

class Command(BaseCommand):
    help = 'Initializes the unmanaged database schema from db/schema.sql with maximum robustness'

    def handle(self, *args, **options):
        self.stdout.write('--- DEFINITIVE SCHEMA INITIALIZATION START ---')
        
        # 1. Locate schema file
        possible_paths = [
            os.path.abspath(os.path.join(settings.BASE_DIR, '..', 'db', 'schema.sql')),
            os.path.abspath(os.path.join(os.getcwd(), '..', 'db', 'schema.sql')),
            os.path.abspath(os.path.join(os.getcwd(), 'db', 'schema.sql')),
            '/opt/render/project/src/db/schema.sql'
        ]
        
        sql_file_path = None
        for p in possible_paths:
            self.stdout.write(f'Checking path: {p}')
            if os.path.exists(p):
                sql_file_path = p
                break

        if not sql_file_path:
            self.stdout.write(self.style.ERROR('CRITICAL: schema.sql could not be located anywhere.'))
            sys.exit(1)

        self.stdout.write(self.style.SUCCESS(f'Found schema at: {sql_file_path}'))

        # 2. Read SQL
        with open(sql_file_path, 'r') as f:
            content = f.read()
        
        # 3. Execute with explicit autocommit
        self.stdout.write('Executing SQL statements...')
        # Postgres allows multi-statement execute, but we'll try to split carefully
        # to ensure "IF NOT EXISTS" doesn't block other statements.
        statements = [s.strip() for s in content.split(';') if s.strip()]
        
        with connection.cursor() as cursor:
            # Important: Ensure we are not in a failed transaction state
            # Django management commands often wrap this.
            for i, stmt in enumerate(statements, 1):
                try:
                    cursor.execute(stmt)
                    self.stdout.write(f'  [{i}/{len(statements)}] OK: {stmt[:50]}...')
                except Exception as e:
                    if 'already exists' in str(e).lower():
                        self.stdout.write(self.style.WARNING(f'  [{i}] Skipped (exists)'))
                    else:
                        self.stdout.write(self.style.ERROR(f'  [{i}] FAILED: {e}'))
                        # Log the problematic SQL
                        self.stdout.write(f'  SQL: {stmt}')
                        # Continue if possible, or exit? 
                        # For creation, failing one usually means others depend on it.
                        sys.exit(1)
        
        # 4. Final Verification
        required_tables = [
            'dim_sector', 'dim_health_label', 'dim_company', 'dim_year',
            'fact_profit_loss', 'fact_balance_sheet', 'fact_cash_flow',
            'fact_analysis', 'fact_pros_cons', 'fact_ml_scores'
        ]
        
        self.stdout.write('--- VERIFYING TABLE CREATION ---')
        with connection.cursor() as cursor:
            cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
            existing = [row[0] for row in cursor.fetchall()]
            
            missing = []
            for table in required_tables:
                if table in existing:
                    self.stdout.write(self.style.SUCCESS(f'  [VERIFIED] {table}'))
                else:
                    self.stdout.write(self.style.ERROR(f'  [MISSING] {table}'))
                    missing.append(table)
            
            if missing:
                self.stdout.write(self.style.ERROR(f'CRITICAL: {len(missing)} tables missing.'))
                sys.exit(1)

        self.stdout.write(self.style.SUCCESS('--- SCHEMA INITIALIZATION COMPLETE ---'))
