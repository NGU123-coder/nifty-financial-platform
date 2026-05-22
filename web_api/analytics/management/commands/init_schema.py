import os
import sys
from django.core.management.base import BaseCommand
from django.db import connection, transaction
from django.conf import settings

class Command(BaseCommand):
    help = 'Initializes the unmanaged database schema from db/schema.sql with robust verification'

    def handle(self, *args, **options):
        self.stdout.write(f'--- SCHEMA INITIALIZATION START ---')
        self.stdout.write(f'Current Working Directory: {os.getcwd()}')
        
        # 1. Locate schema file - check multiple possible locations for Render
        possible_paths = [
            os.path.abspath(os.path.join(settings.BASE_DIR, '..', 'db', 'schema.sql')),
            os.path.abspath(os.path.join(os.getcwd(), '..', 'db', 'schema.sql')),
            os.path.abspath(os.path.join(os.getcwd(), 'db', 'schema.sql')),
        ]
        
        sql_file_path = None
        for p in possible_paths:
            self.stdout.write(f'Checking path: {p}')
            if os.path.exists(p):
                sql_file_path = p
                break
        
        if not sql_file_path:
            self.stdout.write(self.style.ERROR(f'CRITICAL: Schema file not found in any expected location.'))
            # Debug: List directories
            try:
                self.stdout.write(f'Root content: {os.listdir(".")}')
                if os.path.exists(".."):
                    self.stdout.write(f'Parent content: {os.listdir("..")}')
            except:
                pass
            sys.exit(1)

        self.stdout.write(self.style.SUCCESS(f'Found schema at: {sql_file_path}'))

        # 2. Read SQL
        try:
            with open(sql_file_path, 'r') as f:
                full_sql = f.read()
            self.stdout.write(f'Successfully read {len(full_sql)} bytes from schema.sql')
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'CRITICAL: Failed to read schema file: {e}'))
            sys.exit(1)

        # 3. Execute SQL
        self.stdout.write('Connecting to database via raw cursor...')
        with connection.cursor() as cursor:
            # We try executing statements one by one for maximum visibility and error reporting
            statements = [s.strip() for s in full_sql.split(';') if s.strip()]
            self.stdout.write(f'Found {len(statements)} SQL statements to execute.')

            for i, stmt in enumerate(statements, 1):
                # Log a snippet of the statement
                display_stmt = stmt.replace('\n', ' ')[:60] + '...'
                self.stdout.write(f'  [{i}/{len(statements)}] Executing: {display_stmt}')
                
                try:
                    cursor.execute(stmt)
                    # For CREATE statements, we don't necessarily need transaction.atomic() per statement
                    # unless we want to ensure each one is committed immediately.
                    # Standard Django connection is in autocommit mode unless specified.
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'  FAILED statement {i}: {str(e)}'))
                    self.stdout.write(self.style.ERROR(f'  FULL SQL: {stmt}'))
                    sys.exit(1)

        # 4. Final Commit (Just in case)
        try:
            connection.commit()
            self.stdout.write('Database changes committed.')
        except:
            pass

        # 5. Verify Tables Existence in Database
        self.stdout.write('--- VERIFICATION STEP ---')
        required_tables = [
            'dim_sector', 'dim_health_label', 'dim_company', 'dim_year',
            'fact_profit_loss', 'fact_balance_sheet', 'fact_cash_flow',
            'fact_analysis', 'fact_pros_cons', 'fact_ml_scores'
        ]
        
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
            """)
            existing_tables = [row[0] for row in cursor.fetchall()]
            
            missing = []
            for table in required_tables:
                if table in existing_tables:
                    self.stdout.write(self.style.SUCCESS(f'Verified: {table} exists.'))
                else:
                    self.stdout.write(self.style.ERROR(f'MISSING: {table} does not exist!'))
                    missing.append(table)
            
            if missing:
                self.stdout.write(self.style.ERROR(f'CRITICAL FAILURE: {len(missing)} warehouse tables missing after execution.'))
                sys.exit(1)

        self.stdout.write(self.style.SUCCESS('--- SCHEMA INITIALIZATION COMPLETE ---'))
