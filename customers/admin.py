"""
Admin configuration for customer models.
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Customer


@admin.register(Customer)
class CustomerAdmin(UserAdmin):
    """
    Admin interface for Customer model.
    """
    list_display = ('username', 'email', 'full_name', 'phone_number', 'is_active', 'created_at')
    list_filter = ('is_active', 'is_staff', 'sms_notifications_enabled', 'email_notifications_enabled', 'created_at')
    search_fields = ('username', 'email', 'first_name', 'last_name', 'phone_number')
    ordering = ('-created_at',)
    
    fieldsets = UserAdmin.fieldsets + (
        ('Additional Info', {
            'fields': ('phone_number', 'date_of_birth', 'address')
        }),
        ('OpenID Connect', {
            'fields': ('oidc_sub', 'oidc_issuer'),
            'classes': ('collapse',)
        }),
        ('Notification Preferences', {
            'fields': ('sms_notifications_enabled', 'email_notifications_enabled')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('created_at', 'updated_at')
