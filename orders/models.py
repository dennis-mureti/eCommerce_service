"""
Order models for the e-commerce system.
"""
from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal
from customers.models import Customer
from products.models import Product


class Order(models.Model):
    """
    Customer orders with status tracking.
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
    ]
    
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]
    
    # Order identification
    order_number = models.CharField(
        max_length=20,
        unique=True,
        help_text="Unique order number"
    )
    
    customer = models.ForeignKey(
        Customer,
        on_delete=models.PROTECT,
        related_name='orders',
        help_text="Customer who placed the order"
    )
    
    # Order status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        help_text="Current order status"
    )
    
    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default='pending',
        help_text="Payment status"
    )
    
    # Pricing
    subtotal = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Order subtotal (before tax and shipping)"
    )
    
    tax_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        default=Decimal('0.00'),
        help_text="Tax amount"
    )
    
    shipping_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        default=Decimal('0.00'),
        help_text="Shipping cost"
    )
    
    total_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Total order amount"
    )
    
    # Shipping information
    shipping_address = models.TextField(
        help_text="Shipping address"
    )
    
    shipping_phone = models.CharField(
        max_length=17,
        blank=True,
        help_text="Shipping contact phone"
    )
    
    # Order notes
    customer_notes = models.TextField(
        blank=True,
        help_text="Customer notes for the order"
    )
    
    admin_notes = models.TextField(
        blank=True,
        help_text="Internal admin notes"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    shipped_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'orders'
        verbose_name = 'Order'
        verbose_name_plural = 'Orders'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['order_number']),
            models.Index(fields=['customer', 'status']),
            models.Index(fields=['status', 'created_at']),
        ]
    
    def __str__(self):
        return f"Order {self.order_number} - {self.customer.username}"
    
    def save(self, *args, **kwargs):
        """Generate order number if not provided."""
        if not self.order_number:
            import uuid
            self.order_number = f"ORD-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)
    
    @property
    def total_items(self):
        """Return total number of items in the order."""
        return sum(item.quantity for item in self.items.all())
    
    def calculate_totals(self):
        """Calculate and update order totals."""
        self.subtotal = sum(
            item.unit_price * item.quantity 
            for item in self.items.all()
        )
        self.total_amount = self.subtotal + self.tax_amount + self.shipping_amount
        self.save(update_fields=['subtotal', 'total_amount'])


class OrderItem(models.Model):
    """
    Individual items within an order.
    """
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items',
        help_text="Associated order"
    )
    
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        help_text="Ordered product"
    )
    
    quantity = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        help_text="Quantity ordered"
    )
    
    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Unit price at time of order"
    )
    
    # Product snapshot (in case product details change)
    product_name = models.CharField(
        max_length=200,
        help_text="Product name at time of order"
    )
    
    product_sku = models.CharField(
        max_length=50,
        help_text="Product SKU at time of order"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'order_items'
        verbose_name = 'Order Item'
        verbose_name_plural = 'Order Items'
        unique_together = ['order', 'product']
    
    def __str__(self):
        return f"{self.product_name} x {self.quantity}"
    
    @property
    def total_price(self):

        """Return total price for this item."""
        # return self.unit_price * self.quantity
        if self.unit_price is not None and self.quantity is not None:
            return self.unit_price * self.quantity
        return Decimal('0.00')
    
    def save(self, *args, **kwargs):
        """Save product snapshot data."""
        if not self.product_name:
            self.product_name = self.product.name
        if not self.product_sku:
            self.product_sku = self.product.sku
        if not self.unit_price:
            self.unit_price = self.product.price
        super().save(*args, **kwargs)


class OrderStatusHistory(models.Model):
    """
    Track order status changes for audit trail.
    """
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='status_history',
        help_text="Associated order"
    )
    
    from_status = models.CharField(
        max_length=20,
        choices=Order.STATUS_CHOICES,
        null=True,
        blank=True,
        help_text="Previous status"
    )
    
    to_status = models.CharField(
        max_length=20,
        choices=Order.STATUS_CHOICES,
        help_text="New status"
    )
    
    notes = models.TextField(
        blank=True,
        help_text="Notes about the status change"
    )
    
    changed_by = models.ForeignKey(
        Customer,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="User who made the change"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'order_status_history'
        verbose_name = 'Order Status History'
        verbose_name_plural = 'Order Status Histories'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Order {self.order.order_number}: {self.from_status} → {self.to_status}"
