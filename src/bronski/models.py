
# TODO : support "universal" JSON field?
from django.contrib.postgres.fields import JSONField
from django.db import models
from django.utils.module_loading import import_string
from django.utils.timezone import datetime


class CrontabBase(models.Model):
    '''
    Abstract base model for custom Bronski crontab model.
    '''
    crontab = models.CharField(max_length=100)
    function = models.CharField(max_length=255)
    kwargs = JSONField(blank=True)
    is_enabled = models.BooleanField(default=False)
    last_run = models.DateTimeField(default=datetime)

    class Meta:
        abstract = True

    def get_function(self):
        return import_string(self.function)

    def run(self):
        func = self.get_function()
        func(**self.kwargs)
