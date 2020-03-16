
import logging
import threading

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
