"""
Celery tasks for order processing.
"""
from celery import shared_task
from django.utils import timezone
from .models import Order
import logging

logger = logging.getLogger(__name__)


@shared_task
def process_pending_orders():
    """
    Process orders that have been pending for too long.
    """
    # Get orders pending for more than 30 minutes
    cutoff_time = timezone.now() - timezone.timedelta(minutes=30)
    pending_orders = Order.objects.filter(
        status='pending',
        created_at__lt=cutoff_time
    )
    
    processed_count = 0
    for order in pending_orders:
        # Auto-confirm orders with successful payment
        if order.payment_status == 'paid':
            order.status = 'confirmed'
            order.save(update_fields=['status'])
            processed_count += 1
            logger.info(f"Auto-confirmed order: {order.order_number}")
    
    return f"Processed {processed_count} pending orders"


@shared_task
def cleanup_abandoned_carts():
    """
    Clean up old cart sessions (this would need session cleanup logic).
    """
    # This is a placeholder - actual implementation would depend on
    # how you want to handle session cleanup
    logger.info("Cart cleanup task executed")
    return "Cart cleanup completed"


@shared_task
def generate_order_reports():
    """
    Generate daily order reports.
    """
    from django.db.models import Sum, Count
    
    today = timezone.now().date()
    orders_today = Order.objects.filter(created_at__date=today)
    
    report = {
        'date': str(today),
        'total_orders': orders_today.count(),
        'total_revenue': orders_today.aggregate(Sum('total_amount'))['total_amount__sum'] or 0,
        'orders_by_status': {}
    }
    
    # Orders by status
    status_counts = orders_today.values('status').annotate(count=Count('id'))
    for item in status_counts:
        report['orders_by_status'][item['status']] = item['count']
    
    logger.info(f"Daily order report: {report}")
    return report
