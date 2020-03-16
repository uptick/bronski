from datetime import datetime, timedelta

# TODO : support "universal" JSON field?
from django.contrib.postgres.fields import JSONField
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.module_loading import import_string
from django.utils.timezone import now

from croniter import croniter


def cron_validator(value):
    if not croniter.is_valid(value):
        raise ValidationError("Invalid crontab format")


class CrontabBaseManager(models.Manager):

    def missed_jobs(self):
        """
        yields jobs whose last run is longer ago than their crontab frequency.
        """
        now = datetime.now()

        with transaction.atomic():
            qset = (
                self.get_queryset()
                .filter(is_enabled=True)
                # Use skip_locked to catch any new tasks added, and avoid DB error
                .select_for_update(skip_locked=True)
            )
            for job in qset:
                next_run = croniter(job.crontab, job.last_run).get_next(datetime)
                if next_run < now:
                    yield job


class CrontabBase(models.Model):
    '''
    Abstract base model for custom Bronski crontab model.
    '''
    crontab = models.CharField(max_length=100, validators=[cron_validator])
    function = models.CharField(max_length=255)
    kwargs = JSONField(default=dict, blank=True)
    is_enabled = models.BooleanField(default=True)
    last_run = models.DateTimeField(default=now)

    objects = CrontabBaseManager()

    class Meta:
        abstract = True

    def __str__(self):
        return f'{self.function} @ {self.crontab}'

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
