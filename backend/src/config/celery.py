"""
Celery configuration for CPD Events platform.
"""

import os
from celery import Celery
from celery.schedules import crontab

# Set default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')

# Create Celery app
app = Celery('cpd_events')

# Load config from Django settings
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks from all registered Django apps
app.autodiscover_tasks()

# Celery Beat schedule
app.conf.beat_schedule = {
    # Reset subscription usage counters monthly
    'reset-subscription-usage': {
        'task': 'billing.tasks.reset_subscription_usage',
        'schedule': crontab(hour=0, minute=0, day_of_month=1),
    },
    
    # Send trial ending reminders (3 days before)
    'trial-ending-reminders': {
        'task': 'billing.tasks.send_trial_ending_reminders',
        'schedule': crontab(hour=9, minute=0),
    },
    
    # Send event reminders
    'event-reminders-24h': {
        'task': 'events.tasks.send_event_reminders',
        'schedule': crontab(minute=0),  # Every hour
        'kwargs': {'hours_before': 24},
    },
    'event-reminders-1h': {
        'task': 'events.tasks.send_event_reminders',
        'schedule': crontab(minute='*/15'),  # Every 15 min
        'kwargs': {'hours_before': 1},
    },
    
    # Auto-complete ended events
    'auto-complete-events': {
        'task': 'events.tasks.auto_complete_events',
        'schedule': crontab(minute='*/10'),  # Every 10 min
    },
    
    # Cleanup old webhook logs
    'cleanup-webhook-logs': {
        'task': 'integrations.tasks.cleanup_old_logs',
        'schedule': crontab(hour=3, minute=0),  # 3 AM daily
        'kwargs': {'days_old': 30},
    },
    
    # Retry failed webhooks
    'retry-failed-webhooks': {
        'task': 'integrations.tasks.retry_failed_webhooks',
        'schedule': crontab(minute='*/5'),  # Every 5 min
    },
}

# Task routing
app.conf.task_routes = {
    'billing.*': {'queue': 'billing'},
    'certificates.*': {'queue': 'certificates'},
    'events.*': {'queue': 'events'},
    'integrations.*': {'queue': 'integrations'},
}

# Task configuration
app.conf.task_acks_late = True
app.conf.task_reject_on_worker_lost = True
app.conf.worker_prefetch_multiplier = 1


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Debug task for testing Celery connection."""
    print(f'Request: {self.request!r}')
