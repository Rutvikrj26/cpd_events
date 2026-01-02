import json
import logging
from datetime import datetime

from django.conf import settings
from django.urls import reverse
from google.cloud import tasks_v2

logger = logging.getLogger(__name__)

# Registry to store task functions by name
_TASK_REGISTRY = {}


class CloudTask:
    def __init__(self, func, queue='default'):
        self.func = func
        self.queue = queue
        self.name = f"{func.__module__}.{func.__name__}"
        _TASK_REGISTRY[self.name] = self

    def __call__(self, *args, **kwargs):
        """Allow calling the function directly (local execution)."""
        return self.func(*args, **kwargs)

    def delay(self, *args, **kwargs):
        """Push the task to Google Cloud Tasks."""
        if getattr(settings, 'CLOUD_TASKS_SYNC', False):
            # Sync mode: execute immediately instead of queueing
            logger.info(f"Sync mode: Executing task {self.name} immediately.")
            return self.func(*args, **kwargs)

        # Use emulator if configured
        if hasattr(settings, 'CLOUD_TASKS_EMULATOR_HOST') and settings.CLOUD_TASKS_EMULATOR_HOST:
            import os
            os.environ['CLOUD_TASKS_EMULATOR_HOST'] = settings.CLOUD_TASKS_EMULATOR_HOST
            client = tasks_v2.CloudTasksClient()
        else:
            client = tasks_v2.CloudTasksClient()

        project = settings.GCP_PROJECT_ID
        location = settings.GCP_LOCATION
        queue = self.queue

        parent = client.queue_path(project, location, queue)

        # Construct the task payload
        payload = {'task': self.name, 'args': args, 'kwargs': kwargs}
        json_payload = json.dumps(payload)

        # Calculate the target URL (where this Django app handles tasks)
        # Assumes the app is deployed at SITE_URL
        relative_url = reverse('common:cloud_task_handler')
        url = f"{settings.SITE_URL}{relative_url}"

        task = {
            'http_request': {
                'http_method': tasks_v2.HttpMethod.POST,
                'url': url,
                'headers': {'Content-Type': 'application/json'},
                'body': json_payload.encode(),
                'oidc_token': {
                    'service_account_email': settings.GCP_SA_EMAIL,
                },
            }
        }

        try:
            response = client.create_task(request={"parent": parent, "task": task})
            logger.info(f"Created task {response.name}")
            return response
        except Exception as e:
            logger.error(f"Failed to create cloud task: {e}")
            raise

    def schedule(self, eta: datetime, *args, **kwargs):
        """Schedule task for later execution."""
        # Similar to delay but adds schedule_time to the task object
        pass  # To be implemented if needed


def task(queue='default'):
    """Decorator to register a function as a Cloud Task."""

    def decorator(func):
        return CloudTask(func, queue=queue)

    return decorator


def get_task(name):
    """Retrieve a task by name."""
    return _TASK_REGISTRY.get(name)
