import signal
from datetime import datetime
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
        self.stdout.write("Starting Bronski server...")
        job.start()

        # Set up escape hatch
        signal.signal(signal.SIGTERM, job.break_handler)
        signal.signal(signal.SIGINT, job.break_handler)

        # Set up handler for signal
        signal.signal(signal.SIGALRM, job.timer_handler)

        # Align to the minute boundary.
        offset = 60 - datetime.now().second
        # Set OS timer to bug us every minute
        signal.setitimer(signal.ITIMER_REAL, offset, 60)

        while True:
            try:
                sleep(10)
            except ProgramKilled:
                self.stdout.write("Stopping Bronski server...")
                job.stop()
                break
