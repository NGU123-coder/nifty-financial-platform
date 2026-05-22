import os
from django.core.management.base import BaseCommand
from django.db import connection
from django.conf import settings

class Command(BaseCommand):
    help = 'Initializes the unmanaged database schema from db/schema.sql'

    def handle(self, *args, **options):
        sql_file_path = os.path.join(settings.BASE_DIR, '..', 'db', 'schema.sql')
        
        if not os.path.exists(sql_file_path):
            self.stdout.write(self.style.ERROR(f'Schema file not found at {sql_file_path}'))
            return

        self.stdout.write(f'Reading schema from {sql_file_path}...')
        
        with open(sql_file_path, 'r') as f:
            sql = f.read()

        self.stdout.write('Applying schema to database...')
        
        with connection.cursor() as cursor:
            try:
                cursor.execute(sql)
                self.stdout.write(self.style.SUCCESS('Successfully applied unmanaged schema.'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error applying schema: {str(e)}'))
