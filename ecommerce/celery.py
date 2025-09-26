"""
Celery configuration for ecommerce project.
"""
import os
from celery import Celery
from celery.schedules import crontab

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecommerce.settings')

app = Celery('ecommerce')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

# Periodic tasks
app.conf.beat_schedule = {
    'process-pending-orders': {
        'task': 'orders.tasks.process_pending_orders',
        'schedule': crontab(minute='*/15'),  # Every 15 minutes
    },
    'cleanup-abandoned-carts': {
        'task': 'orders.tasks.cleanup_abandoned_carts',
        'schedule': crontab(hour=2, minute=0),  # Daily at 2 AM
    },
    'generate-order-reports': {
        'task': 'orders.tasks.generate_order_reports',
        'schedule': crontab(hour=23, minute=55),  # Daily at 11:55 PM
    },
    'check-low-stock-products': {  # Added low stock check task
        'task': 'notifications.tasks.check_low_stock_products',
        'schedule': crontab(hour='*/6', minute=0),  # Every 6 hours
    },
    'retry-failed-notifications': {  # Added retry failed notifications task
        'task': 'notifications.tasks.retry_failed_notifications',
        'schedule': crontab(hour='*/2', minute=30),  # Every 2 hours at 30 minutes
    },
    'cleanup-old-notifications': {  # Added notification cleanup task
        'task': 'notifications.tasks.cleanup_old_notifications',
        'schedule': crontab(hour=1, minute=0),  # Daily at 1 AM
    },
}

app.conf.timezone = 'Africa/Nairobi'

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
