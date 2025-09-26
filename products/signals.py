"""
Signal handlers for product events.
"""
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from .models import Product, ProductImage
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Product)
def product_created_updated(sender, instance, created, **kwargs):
    """
    Handle product creation and updates.
    """
    if created:
        logger.info(f"New product created: {instance.name} ({instance.sku})")
        
        # Could trigger notifications for new products
        # Will implement in notifications task
    else:
        logger.info(f"Product updated: {instance.name} ({instance.sku})")


@receiver(pre_save, sender=Product)
def check_stock_levels(sender, instance, **kwargs):
    """
    Check stock levels and log warnings.
    """
    if instance.pk:  # Only for existing products
        try:
            old_instance = Product.objects.get(pk=instance.pk)
            
            # Check if stock went from in-stock to out-of-stock
            if old_instance.stock_quantity > 0 and instance.stock_quantity == 0:
                logger.warning(f"Product out of stock: {instance.name} ({instance.sku})")
            
            # Check if stock went below threshold
            elif (old_instance.stock_quantity > old_instance.low_stock_threshold and 
                  instance.stock_quantity <= instance.low_stock_threshold):
                logger.warning(f"Low stock alert: {instance.name} ({instance.sku}) - {instance.stock_quantity} remaining")
                
        except Product.DoesNotExist:
            pass


@receiver(post_save, sender=ProductImage)
def product_image_uploaded(sender, instance, created, **kwargs):
    """
    Handle product image uploads.
    """
    if created:
        logger.info(f"New image uploaded for product: {instance.product.name}")
        
        # If this is the first image, make it primary
        if not instance.product.images.filter(is_primary=True).exists():
            instance.is_primary = True
            instance.save(update_fields=['is_primary'])
