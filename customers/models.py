"""
Customer models for the e-commerce system.
"""
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import RegexValidator


class Customer(AbstractUser):
    """
    Extended user model for customers with additional fields.
    """
    phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
    )
    
    phone_number = models.CharField(
        validators=[phone_regex],
        max_length=17,
        blank=True,
        help_text="Customer's phone number for SMS notifications"
    )
    
    date_of_birth = models.DateField(
        null=True,
        blank=True,
        help_text="Customer's date of birth"
    )
    
    address = models.TextField(
        blank=True,
        help_text="Customer's physical address"
    )
    
    # OpenID Connect fields
    oidc_sub = models.CharField(
        max_length=255,
        unique=True,
        null=True,
        blank=True,
        help_text="OpenID Connect subject identifier"
    )
    
    oidc_issuer = models.CharField(
        max_length=255,
        blank=True,
        help_text="OpenID Connect issuer"
    )
    
    # Preferences
    sms_notifications_enabled = models.BooleanField(
        default=True,
        help_text="Whether customer wants to receive SMS notifications"
    )
    
    email_notifications_enabled = models.BooleanField(
        default=True,
        help_text="Whether customer wants to receive email notifications"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'customers'
        verbose_name = 'Customer'
        verbose_name_plural = 'Customers'
    
    def __str__(self):
        return f"{self.username} ({self.email})"
    
    @property
    def full_name(self):
        """Return the customer's full name."""
        return f"{self.first_name} {self.last_name}".strip()
