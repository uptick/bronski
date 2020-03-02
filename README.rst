=======
Bronski
=======

.. rubric:: A beat server for Django, with cron-like syntax

Bronski allows you to configure periodic function calls using a Django model.

It is ideally suited to being a task "beat" sever, akin to celery-beat.

Install
-------

    $ pip install bronski


Setup
-----

1. Create a model in your own app that inherits from `bronski.models.CrontabBase`

2. Run ``manage.py makemigrations`` and ``manage.py migrate``

3. Specify your model in settings

    CRONTAB_MODEL = "myapp.MyCronModel"

4. Launch your beat server:

    $ ./manage.py bronski

Each minute the `bronski` service will scan the model for active tasks that
haven't been run in the past 59 seconds. It will then check each to see if its
crontab definition matches the next minute.

For job records that match, their `run` method will be called. The default
`run` method first calls `self.get_function()` to import the function
specified in the `function` field, then invokes it, passing the `kwargs` field
as keyword arguments.

You can override `run` in your custom model to, for instance, enqueue jobs:

.. code-block:: python

    class Tasks(CrontabBase):

        def run(self):
            func = self.get_function()
            # Celery task API:
            func.delay(**self.kwargs)
            # Dramatiq actor API:
            func.send(**self.kwargs)
