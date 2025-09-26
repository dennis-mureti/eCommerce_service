"""
Signal handlers for customer events.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.signals import user_logged_in, user_logged_out
from .models import Customer
from notifications.tasks import send_welcome_message_async
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Customer)
def customer_created(sender, instance, created, **kwargs):
    """
    Handle customer creation events.
    """
    if created:
        logger.info(f"New customer created: {instance.email}")
        
        # Only attempt to send welcome message if Celery is available
        try:
            from celery import current_app
            if not current_app.conf.task_always_eager:
                send_welcome_message_async.delay(instance.id)
        except Exception as e:
            logger.warning(f"Could not send welcome message, (Celery may not be running): {e}")

@receiver(user_logged_in)
def customer_logged_in(sender, request, user, **kwargs):
    """
    Handle customer login events.
    """
    if hasattr(user, 'phone_number'):  # Check if it's a Customer instance
        logger.info(f"Customer logged in: {user.email}")


@receiver(user_logged_out)
def customer_logged_out(sender, request, user, **kwargs):
    """
    Handle customer logout events.
    """
    if user and hasattr(user, 'phone_number'):
        logger.info(f"Customer logged out: {user.email}")
