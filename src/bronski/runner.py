
import logging
import signal
import threading
from datetime import datetime

import django
from django.db import close_old_connections
from django.db.models.functions import Now

django.setup()

log = logging.getLogger(__name__)


class ProgramKilled(Exception):
    pass


class JobRunner(threading.Thread):
    def __init__(self, model):
        super().__init__()
        self.trigger = threading.Event()
        self.stopped = threading.Event()

        self.model = model

    def setup_signals(self):
        # Set up escape hatch
        signal.signal(signal.SIGTERM, self.break_handler)
        signal.signal(signal.SIGINT, self.break_handler)

        # Set up handler for signal
        signal.signal(signal.SIGALRM, self.timer_handler)

        # Align to the minute boundary.
        offset = 60 - datetime.now().second
        # Set OS timer to bug us every minute
        signal.setitimer(signal.ITIMER_REAL, offset, 60)

    def timer_handler(self, signum, frame):
        '''Signal handler for timer.'''
        log.debug("Scanning jobs...")
        self.trigger.set()

    @staticmethod
    def break_handler(signum, frame):
        '''Signal handler for ctrl-c / SIGTERM, to exit program.'''
        log.info("Detected stop request...")
        raise ProgramKilled

    def stop(self):
        log.info("Setting stop...")
        self.stopped.set()
        self.trigger.set()
        self.join()

    def run(self):
        log.info("Starting Bronski Runner...")
        while self.trigger.wait():
            if self.stopped.is_set():
                log.info("Stopping...")
                break

            for job in self.model.objects.current_jobs():
                log.info("Running job: %s", job)
                try:
                    job.run()
                    job.last_run = Now()
                    job.mark_run()
                except Exception:
                    log.exception("Failed running job: %s", job)

            # Clean up django DB connections
            close_old_connections()

            # Reset our trigger
            self.trigger.clear()
