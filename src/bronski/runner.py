
import logging
import threading
from datetime import datetime, timedelta

import django
from croniter import croniter
from django.db import close_old_connections, transaction
from django.db.models.functions import Now
from django.utils import timezone

django.setup()

log = logging.getLogger(__name__)


class ProgramKilled(Exception):
    pass


class TaskRunner(threading.Thread):
    def __init__(self, model):
        super().__init__()
        self.trigger = threading.Event()
        self.stopped = threading.Event()

        self.model = model

    def timer_handler(self, signum, frame):
        '''Signal handler for timer.'''
        log.debug("Scanning tasks...")
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

            now = timezone.localtime(timezone.now())

            with transaction.atomic():
                qset = (
                    self.model.objects
                    .filter(is_enabled=True, last_run__lt=Now() - timedelta(seconds=59))
                    # Use skip_locked to catch any new tasks added, and avoid DB error
                    .select_for_update(skip_locked=True)
                )
                for task in qset:
                    next_run = croniter(task.crontab, now).get_next(datetime)
                    if (next_run - now) < timedelta(minutes=1):
                        log.info("Enqueueing task: %s", task)
                        task.run()
                    else:
                        log.info("Skipping task: %s", task)

                qset.update(last_run=Now())

            # Clean up django DB connections
            close_old_connections()

            # Reset our trigger
            self.trigger.clear()
