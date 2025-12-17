from django.urls import path

from .views import CloudTaskHandlerView

app_name = 'common'

urlpatterns = [
    path('tasks/handler/', CloudTaskHandlerView.as_view(), name='cloud_task_handler'),
]
