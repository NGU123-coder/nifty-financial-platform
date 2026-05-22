import os
import sys
from django.core.management.base import BaseCommand
from django.db import connection, transaction
from django.conf import settings

class Command(BaseCommand):
    help = 'Initializes the unmanaged database schema from db/schema.sql with robust logging'

    def handle(self, *args, **options):
        sql_file_path = os.path.join(settings.BASE_DIR, '..', 'db', 'schema.sql')
        
        if not os.path.exists(sql_file_path):
            self.stdout.write(self.style.ERROR(f'CRITICAL: Schema file not found at {sql_file_path}'))
            sys.exit(1)

        self.stdout.write(f'Reading schema from {sql_file_path}...')
        
        with open(sql_file_path, 'r') as f:
            full_sql = f.read()

        # Split SQL into individual statements
        # Note: This is a simple split by semicolon. 
        # It works for our schema but might need adjustment for complex SQL.
        statements = [s.strip() for s in full_sql.split(';') if s.strip()]

        self.stdout.write(f'Found {len(statements)} SQL statements to execute.')

        with connection.cursor() as cursor:
            for i, stmt in enumerate(statements, 1):
                # Clean up the statement for logging
                first_line = stmt.split('\n')[0][:50] + '...'
                self.stdout.write(f'[{i}/{len(statements)}] Executing: {first_line}')
                
                try:
                    with transaction.atomic():
                        cursor.execute(stmt)
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'FAILED statement {i}: {str(e)}'))
                    self.stdout.write(self.style.ERROR(f'FULL STATEMENT: {stmt}'))
                    # We exit with 1 to tell Render the deployment failed
                    sys.exit(1)

        self.stdout.write(self.style.SUCCESS('Successfully initialized ALL warehouse tables and indexes.'))
