# notifications/tasks_sync.py
import logging
from .models import Notification
from orders.models import Order

logger = logging.getLogger(__name__)

def send_order_confirmation_sync(order_id):
    """
    Synchronous version of order confirmation email.
    """
    try:
        order = Order.objects.get(id=order_id)
        logger.info(f"Sending order confirmation for order {order.order_number}")
        # Add your email sending logic here
        # For example:
        # send_mail(...)
        logger.info(f"Order confirmation sent for {order.order_number}")
    except Exception as e:
        logger.error(f"Error sending order confirmation: {str(e)}")
        raise