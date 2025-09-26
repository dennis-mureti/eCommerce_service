"""
Celery tasks for notification processing.
"""
from celery import shared_task
from django.utils import timezone
from .models import Notification
from .services import notification_service
from customers.models import Customer
from products.models import Product
import logging

logger = logging.getLogger(__name__)


@shared_task
def send_notification_async(recipient_id, notification_type, context=None, channel=None):
    """
    Send notification asynchronously.
    
    Args:
        recipient_id (int): Customer ID
        notification_type (str): Type of notification
        context (dict): Template context data
        channel (str): Notification channel
    """
    try:
        recipient = Customer.objects.get(id=recipient_id)
        result = notification_service.send_notification(
            recipient=recipient,
            notification_type=notification_type,
            context=context or {},
            channel=channel
        )
        
        logger.info(f"Async notification sent to {recipient.email}: {notification_type}")
        return result
        
    except Customer.DoesNotExist:
        logger.error(f"Customer not found: {recipient_id}")
        return {'error': 'Customer not found'}
    except Exception as e:
        logger.error(f"Async notification error: {str(e)}")
        return {'error': str(e)}


@shared_task
def send_order_confirmation_async(order_id):
    """
    Send order confirmation notification asynchronously.
    """
    try:
        from orders.models import Order
        order = Order.objects.get(id=order_id)
        result = notification_service.send_order_confirmation(order)
        
        logger.info(f"Order confirmation sent for order: {order.order_number}")
        return result
        
    except Order.DoesNotExist:
        logger.error(f"Order not found: {order_id}")
        return {'error': 'Order not found'}
    except Exception as e:
        logger.error(f"Order confirmation error: {str(e)}")
        return {'error': str(e)}


@shared_task
def send_order_status_notification_async(order_id, status):
    """
    Send order status change notification asynchronously.
    """
    try:
        from orders.models import Order
        order = Order.objects.get(id=order_id)
        
        if status == 'shipped':
            result = notification_service.send_order_shipped(order)
        elif status == 'delivered':
            result = notification_service.send_order_delivered(order)
        elif status == 'cancelled':
            result = notification_service.send_order_cancelled(order)
        else:
            return {'error': f'Unsupported status: {status}'}
        
        logger.info(f"Order status notification sent for order: {order.order_number} - {status}")
        return result
        
    except Order.DoesNotExist:
        logger.error(f"Order not found: {order_id}")
        return {'error': 'Order not found'}
    except Exception as e:
        logger.error(f"Order status notification error: {str(e)}")
        return {'error': str(e)}


@shared_task
def send_welcome_message_async(customer_id):
    """
    Send welcome message to new customer asynchronously.
    """
    try:
        customer = Customer.objects.get(id=customer_id)
        result = notification_service.send_welcome_message(customer)
        
        logger.info(f"Welcome message sent to: {customer.email}")
        return result
        
    except Customer.DoesNotExist:
        logger.error(f"Customer not found: {customer_id}")
        return {'error': 'Customer not found'}
    except Exception as e:
        logger.error(f"Welcome message error: {str(e)}")
        return {'error': str(e)}


@shared_task
def check_low_stock_products():
    """
    Check for low stock products and send alerts.
    """
    try:
        # Get products with low stock
        low_stock_products = Product.objects.filter(
            is_active=True,
            stock_quantity__lte=models.F('low_stock_threshold')
        )
        
        if not low_stock_products.exists():
            return "No low stock products found"
        
        # Get admin users
        admin_users = Customer.objects.filter(
            is_staff=True,
            is_active=True,
            email_notifications_enabled=True
        )
        
        if not admin_users.exists():
            logger.warning("No admin users found for low stock alerts")
            return "No admin users found"
        
        # Send alerts for each low stock product
        alerts_sent = 0
        for product in low_stock_products:
            results = notification_service.send_low_stock_alert(product, admin_users)
            alerts_sent += len([r for r in results if r.get('email', {}).get('success')])
        
        logger.info(f"Low stock alerts sent: {alerts_sent}")
        return f"Low stock alerts sent: {alerts_sent}"
        
    except Exception as e:
        logger.error(f"Low stock check error: {str(e)}")
        return {'error': str(e)}


@shared_task
def retry_failed_notifications():
    """
    Retry failed notifications.
    """
    try:
        # Get failed notifications from last 24 hours
        cutoff_time = timezone.now() - timezone.timedelta(hours=24)
        failed_notifications = Notification.objects.filter(
            status='failed',
            created_at__gte=cutoff_time
        )
        
        retried_count = 0
        success_count = 0
        
        for notification in failed_notifications:
            try:
                if notification.channel == 'sms':
                    result = notification_service.sms_service.send_sms(
                        notification.recipient_address,
                        notification.message,
                        notification.id
                    )
                elif notification.channel == 'email':
                    result = notification_service.email_service.send_email(
                        notification.recipient_address,
                        notification.subject,
                        notification.message,
                        notification_id=notification.id
                    )
                else:
                    continue
                
                retried_count += 1
                if result.get('success'):
                    success_count += 1
                    
            except Exception as e:
                logger.error(f"Retry notification error: {str(e)}")
                continue
        
        logger.info(f"Retried {retried_count} notifications, {success_count} successful")
        return f"Retried {retried_count} notifications, {success_count} successful"
        
    except Exception as e:
        logger.error(f"Retry failed notifications error: {str(e)}")
        return {'error': str(e)}


@shared_task
def cleanup_old_notifications():
    """
    Clean up old notification records.
    """
    try:
        # Delete notifications older than 90 days
        cutoff_date = timezone.now() - timezone.timedelta(days=90)
        deleted_count = Notification.objects.filter(
            created_at__lt=cutoff_date
        ).delete()[0]
        
        logger.info(f"Cleaned up {deleted_count} old notifications")
        return f"Cleaned up {deleted_count} old notifications"
        
    except Exception as e:
        logger.error(f"Notification cleanup error: {str(e)}")
        return {'error': str(e)}
