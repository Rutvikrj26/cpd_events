from django.urls import path

from .cron_views import CronTickView
from .views import CloudTaskHandlerView

app_name = 'common'

urlpatterns = [
    path('tasks/handler/', CloudTaskHandlerView.as_view(), name='cloud_task_handler'),
    path('cron/tick/', CronTickView.as_view(), name='cron_tick'),
]
