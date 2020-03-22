from time import sleep

from django.apps import apps
from django.conf import settings
from django.core.management.base import BaseCommand

from bronski.runner import ProgramKilled, JobRunner


class Command(BaseCommand):
    help = "Start a bronski beat server"

    def handle(self, *args, **options):
        model = apps.get_model(settings.CRONTAB_MODEL)
        job = JobRunner(model)
        job.setup_signals()
        self.stdout.write("Starting Bronski server...")
        job.start()

        while True:
            try:
                sleep(10)
            except ProgramKilled:
                self.stdout.write("Stopping Bronski server...")
                job.stop()
                break
