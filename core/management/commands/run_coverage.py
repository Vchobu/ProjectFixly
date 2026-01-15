# Django management command to run external commands

import subprocess
import sys
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Run tests with coverage'

    def handle(self, *args, **options):
        subprocess.run([sys.executable, '-m', 'pip', 'install', 'coverage', '-q'])
        subprocess.run([sys.executable, '-m', 'coverage', 'run', '--source=core', 'manage.py', 'test', 'core.tests'])
        subprocess.run([sys.executable, '-m', 'coverage', 'report', '-m'])
        subprocess.run([sys.executable, '-m', 'coverage', 'html'])
        self.stdout.write('Done! Open htmlcov/index.html')