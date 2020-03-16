from django.contrib import admin
from django.db.models.functions import Now


def trigger_task(self, request, queryset):
    for task in queryset:
        task.run()
    queryset.update(last_run=Now())

trigger_task.short_description = 'Run Selected...'


class CrontabBaseAdmin(admin.ModelAdmin):
    list_display = ('crontab', 'function', 'kwargs', 'is_enabled', 'last_run',)
    list_display_links = ('function',)
    list_filter = ('is_enabled',)
    list_editable = ('is_enabled',)
    date_hierarchy = 'last_run'

    actions = [
        trigger_task,
    ]
