=======
Bronski
=======

.. rubric:: A beat server for Django, with cron-like syntax

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
