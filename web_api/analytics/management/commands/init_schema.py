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
        sql_file_path = os.path.abspath(os.path.join(settings.BASE_DIR, '..', 'db', 'schema.sql'))
        if not os.path.exists(sql_file_path):
            # Fallback for Render directory structure if BASE_DIR/.. fails
            sql_file_path = os.path.abspath(os.path.join(os.getcwd(), 'db', 'schema.sql'))
            if not os.path.exists(sql_file_path):
                # Another fallback: search in current and parent
                self.stdout.write(self.style.ERROR(f'Schema file NOT found at standard paths. Searching...'))
                for root, dirs, files in os.walk('/opt/render/project/src'):
                    if 'schema.sql' in files:
                        sql_file_path = os.path.join(root, 'schema.sql')
                        break

        if not sql_file_path or not os.path.exists(sql_file_path):
            self.stdout.write(self.style.ERROR('CRITICAL: schema.sql could not be located anywhere.'))
            sys.exit(1)

        self.stdout.write(f'Using schema file: {sql_file_path}')

        # 2. Read and Split SQL
        with open(sql_file_path, 'r') as f:
            content = f.read()
        
        # Split by semicolon but handle potential issues
        statements = [s.strip() for s in content.split(';') if s.strip()]
        self.stdout.write(f'Found {len(statements)} SQL statements to execute.')

        # 3. Execute with explicit connection and commit
        with connection.cursor() as cursor:
            for i, stmt in enumerate(statements, 1):
                try:
                    self.stdout.write(f'[{i}/{len(statements)}] Executing: {stmt[:50].replace("\n", " ")}...')
                    cursor.execute(stmt)
                    # We don't call commit here because we want the block to succeed or fail
                except Exception as e:
                    # Ignore "already exists" errors to allow re-runs
                    if 'already exists' in str(e).lower():
                        self.stdout.write(self.style.WARNING(f'  Skipped: already exists.'))
                    else:
                        self.stdout.write(self.style.ERROR(f'  FAILED statement {i}: {e}'))
                        self.stdout.write(self.style.ERROR(f'  Full SQL: {stmt}'))
                        sys.exit(1)
        
        # Explicit commit for the entire session
        try:
            # Depending on the connection mode, this might be needed
            if not connection.get_autocommit():
                connection.commit()
                self.stdout.write('Explicitly committed changes.')
        except:
            pass

        # 4. Final Verification
        required_tables = [
            'dim_sector', 'dim_health_label', 'dim_company', 'dim_year',
            'fact_profit_loss', 'fact_balance_sheet', 'fact_cash_flow',
            'fact_analysis', 'fact_pros_cons', 'fact_ml_scores'
        ]
        
        self.stdout.write('--- FINAL VERIFICATION ---')
        with connection.cursor() as cursor:
            cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
            existing = [row[0] for row in cursor.fetchall()]
            
            all_good = True
            for table in required_tables:
                if table in existing:
                    self.stdout.write(self.style.SUCCESS(f'OK: {table} verified.'))
                else:
                    self.stdout.write(self.style.ERROR(f'CRITICAL: {table} is still MISSING!'))
                    all_good = False
            
            if not all_good:
                sys.exit(1)

        self.stdout.write(self.style.SUCCESS('--- DEFINITIVE SCHEMA INITIALIZATION COMPLETE ---'))
