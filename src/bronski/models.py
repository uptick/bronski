from datetime import datetime, timedelta

# TODO : support "universal" JSON field?
from django.contrib.postgres.fields import JSONField
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models.functions import Now
from django.utils.module_loading import import_string
from django.utils import timezone

from croniter import croniter


def cron_validator(value):
    if not croniter.is_valid(value):
        raise ValidationError("Invalid crontab format")


class CrontabBaseQuerySet(models.QuerySet):
    def enabled(self):
        return self.filter(is_enabled=True)

    @staticmethod
    def now():
        """
        We have fiddly requirements for `now`.

        `croniter` has issues if you pass it the current time in UTC, and will
        give you a datetime with UTC timezone, but adjusted to system local
        timezone.

        To correct for this, we set the current timezone.

        Additionally, asking for `get_next`, if the current time matches the
        crontab pattern, `croniter` will return the _next_ time.

        To correct for this, we subtract one second from the time.

        Setting microsecond to 0 is just tidiness.
        """
        return timezone.localtime(
            timezone.now().replace(microsecond=0) - timedelta(seconds=1)
        )

    def scan_jobs(self):
        """
        Convenience function for scanning a set of Jobs exclusively.

        Affects DB level locking.
        """
        with transaction.atomic():
            for job in self.select_for_update(skip_locked=True):
                yield job

    def current_jobs(self):
        """
        Yield jobs which should be run this minute.
        """
        now = self.now()

        for job in (
            self.enabled()
            .filter(last_run__lt=Now() - timedelta(seconds=59))
            .scan_jobs()
        ):
            next_run = croniter(job.crontab, now).get_next(datetime)
            if (next_run - now) < timedelta(minutes=1):
                yield job

    def missed_jobs(self):
        """
        yields jobs whose last run is longer ago than their crontab frequency.
        """
        now = self.now()

        for job in self.enabled().scan_jobs():
            next_run = croniter(job.crontab, job.last_run).get_next(datetime)
            if next_run < now:
                yield job


class CrontabBase(models.Model):
    """
    Abstract base model for custom Bronski crontab model.
    """

    crontab = models.CharField(max_length=100, validators=[cron_validator])
    function = models.CharField(max_length=255)
    kwargs = JSONField(default=dict, blank=True)
    is_enabled = models.BooleanField(default=True)
    last_run = models.DateTimeField(default=timezone.now)

    objects = CrontabBaseQuerySet.as_manager()

    class Meta:
        abstract = True

    def __str__(self):
        return f"{self.function} @ {self.crontab}"

    def get_function(self):
        """Helper to import the named function in `function`."""
        return import_string(self.function)

    def get_kwargs(self):
        """Hepler to return the kwargs field or default to empty dict."""
        return self.kwargs or {}

    def run(self):
        func = self.get_function()
        kwargs = self.get_kwargs()
        func(**kwargs)

    def mark_run(self):
        """
        Update the last_run to Now, and save.
        """
        self.last_run = Now()
        self.save()
        self.refresh_from_db()
