import os
from django.core.management.base import BaseCommand
from django.db import connection
from django.conf import settings

class Command(BaseCommand):
    help = 'Initializes the data warehouse schema (PostgreSQL tables)'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('--- STARTING WAREHOUSE SETUP ---'))
        
        # Determine schema path - relative to project root
        # Base dir is web_api, so we go up one level
        project_root = os.path.dirname(settings.BASE_DIR)
        schema_path = os.path.join(project_root, 'db', 'schema.sql')
        
        if not os.path.exists(schema_path):
            self.stdout.write(self.style.ERROR(f'Schema file not found at: {schema_path}'))
            return

        self.stdout.write(f'Reading schema from: {schema_path}')
        
        with open(schema_path, 'r') as f:
            sql = f.read()

        try:
            with connection.cursor() as cursor:
                self.stdout.write('Executing SQL schema...')
                cursor.execute(sql)
            self.stdout.write(self.style.SUCCESS('--- WAREHOUSE SCHEMA INITIALIZED SUCCESSFULLY ---'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error initializing warehouse: {e}'))
            raise e
