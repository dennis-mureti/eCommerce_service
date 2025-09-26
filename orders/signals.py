"""
Signal handlers for order events.
"""
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from .models import Order, OrderStatusHistory
from notifications.tasks import send_order_confirmation_async, send_order_status_notification_async
import logging
from notifications.tasks import send_order_confirmation_async
from notifications.tasks_sync import send_order_confirmation_sync
logger = logging.getLogger(__name__)


# @receiver(post_save, sender=Order)
# def order_created_updated(sender, instance, created, **kwargs):
#     """
#     Handle order creation and updates.
#     """
#     if created:
#         logger.info(f"New order created: {instance.order_number} for {instance.customer.email}")
        
#         # Send order confirmation notification asynchronously
#         send_order_confirmation_async.delay(instance.id)
#     else:
#         logger.info(f"Order updated: {instance.order_number}")
@receiver(post_save, sender=Order)
def order_created_updated(sender, instance, created, **kwargs):
    """
    Handle order creation and updates.
    """ 
    if created:
        logger.info(f"New order created: {instance.order_number} for {instance.customer.email}")
        
        try:
            # Try to send confirmation asynchronously 
            send_order_confirmation_async(instance.id)
        except Exception as e:
            logger.error(f"Failed to queue order confirmation email: {str(e)}")
            # Fall back to synchronous sending if async fails
            try:
                from notifications.tasks import send_order_confirmation_sync
                send_order_confirmation_sync(instance.id)
            except Exception as sync_error:
                logger.error(f"Failed to send order confirmation: {str(sync_error)}")
    else:
        logger.info(f"Order updated: {instance.order_number}")


@receiver(post_save, sender=OrderStatusHistory)
def order_status_changed(sender, instance, created, **kwargs):
    """
    Handle order status changes.
    """
    if created:
        logger.info(f"Order {instance.order.order_number} status changed: {instance.from_status} → {instance.to_status}")
        
        # Send status change notifications for specific statuses
        if instance.to_status in ['shipped', 'delivered', 'cancelled']:
            send_order_status_notification_async.delay(
                instance.order.id,
                instance.to_status
            )


@receiver(pre_save, sender=Order)
def order_pre_save(sender, instance, **kwargs):
    """
    Handle order pre-save operations.
    """
    # Ensure total amount is calculated correctly
    if instance.subtotal is not None:
        instance.total_amount = instance.subtotal + instance.tax_amount + instance.shipping_amount
