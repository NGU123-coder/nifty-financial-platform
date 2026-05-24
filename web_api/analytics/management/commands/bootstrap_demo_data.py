import os
from django.core.management.base import BaseCommand
from django.db import connection
from django.conf import settings

class Command(BaseCommand):
    help = 'Seeds the database with initial demo data'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('--- STARTING DEMO DATA BOOTSTRAP ---'))
        
        project_root = os.path.dirname(settings.BASE_DIR)
        bootstrap_path = os.path.join(project_root, 'manual_render_bootstrap.sql')
        
        if not os.path.exists(bootstrap_path):
            self.stdout.write(self.style.ERROR(f'Bootstrap file not found at: {bootstrap_path}'))
            return

        self.stdout.write(f'Reading bootstrap data from: {bootstrap_path}')
        
        with open(bootstrap_path, 'r') as f:
            sql = f.read()

        try:
            with connection.cursor() as cursor:
                self.stdout.write('Executing Bootstrap SQL...')
                cursor.execute(sql)
            self.stdout.write(self.style.SUCCESS('--- DEMO DATA BOOTSTRAPPED SUCCESSFULLY ---'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error bootstrapping data: {e}'))
            raise e
