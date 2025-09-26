"""
Notification models for SMS and email notifications.
"""
from django.db import models
from customers.models import Customer
from orders.models import Order


class NotificationTemplate(models.Model):
    """
    Templates for different types of notifications.
    """
    NOTIFICATION_TYPES = [
        ('order_confirmation', 'Order Confirmation'),
        ('order_shipped', 'Order Shipped'),
        ('order_delivered', 'Order Delivered'),
        ('order_cancelled', 'Order Cancelled'),
        ('low_stock_alert', 'Low Stock Alert'),
        ('welcome', 'Welcome Message'),
    ]
    
    CHANNEL_CHOICES = [
        ('sms', 'SMS'),
        ('email', 'Email'),
    ]
    
    name = models.CharField(
        max_length=100,
        help_text="Template name"
    )
    
    notification_type = models.CharField(
        max_length=50,
        choices=NOTIFICATION_TYPES,
        help_text="Type of notification"
    )
    
    channel = models.CharField(
        max_length=10,
        choices=CHANNEL_CHOICES,
        help_text="Notification channel"
    )
    
    subject = models.CharField(
        max_length=200,
        blank=True,
        help_text="Email subject (not used for SMS)"
    )
    
    message = models.TextField(
        help_text="Message template with placeholders"
    )
    
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this template is active"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'notification_templates'
        verbose_name = 'Notification Template'
        verbose_name_plural = 'Notification Templates'
        unique_together = ['notification_type', 'channel']
    
    def __str__(self):
        return f"{self.name} ({self.channel})"


class Notification(models.Model):
    """
    Individual notification records for tracking.
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
        ('delivered', 'Delivered'),
    ]
    
    CHANNEL_CHOICES = [
        ('sms', 'SMS'),
        ('email', 'Email'),
    ]
    
    recipient = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name='notifications',
        help_text="Notification recipient"
    )
    
    channel = models.CharField(
        max_length=10,
        choices=CHANNEL_CHOICES,
        help_text="Notification channel"
    )
    
    notification_type = models.CharField(
        max_length=50,
        help_text="Type of notification"
    )
    
    subject = models.CharField(
        max_length=200,
        blank=True,
        help_text="Email subject"
    )
    
    message = models.TextField(
        help_text="Notification message"
    )
    
    recipient_address = models.CharField(
        max_length=255,
        help_text="Email address or phone number"
    )
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        help_text="Notification status"
    )
    
    # Related objects
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='notifications',
        help_text="Related order (if applicable)"
    )
    
    # Delivery tracking
    external_id = models.CharField(
        max_length=100,
        blank=True,
        help_text="External service message ID"
    )
    
    error_message = models.TextField(
        blank=True,
        help_text="Error message if delivery failed"
    )
    
    sent_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'notifications'
        verbose_name = 'Notification'
        verbose_name_plural = 'Notifications'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'status']),
            models.Index(fields=['channel', 'status']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.notification_type} to {self.recipient.username} via {self.channel}"
