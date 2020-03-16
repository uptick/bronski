=======
Bronski
=======

.. rubric:: A beat server for Django, with cron-like syntax

Bronski allows you to configure periodic function calls using a Django model.

It is ideally suited to being a task "beat" sever, akin to celery-beat.

Install
-------

.. code-block:: sh

    $ pip install bronski


Setup
-----

1. Add 'bronski' to your ``INSTALLED_APPS``

   This is only needed to enable the management command.

2. Create a model in your own app that inherits from ``bronski.models.CrontabBase``

3. Create and apply migrations:

   .. code-block:: sh

    $ manage.py makemigrations
    $ manage.py migrate

4. Specify your model in settings

   .. code-block:: python

    CRONTAB_MODEL = "myapp.MyCronModel"

5. Launch your beat server:

   .. code-block:: sh

    $ ./manage.py bronski

Each minute the ``bronski`` service will scan the model for enabled jobs that
haven't been run in the past 59 seconds. It will then check each to see if its
crontab definition matches the next minute.

For job records that match, their ``run`` method will be called. The default
``run`` method will:

- get the specified function by calling ``self.get_function()``
- resolve the ``kwargs`` to use by calling ``self.get_kwargs()``
- invoke the function with the ``kwargs``.

You can override ``run`` in your custom model to, for instance, enqueue jobs:

.. code-block:: python

    class Jobs(CrontabBase):

        def run(self):
            func = self.get_function()
            kwargs = self.get_kwargs()

            # Celery task API:
            func.delay(**kwargs)
            # Dramatiq actor API:
            func.send(**kwargs)
