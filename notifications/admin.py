"""
Admin configuration for notification models.
"""
from django.contrib import admin
from .models import NotificationTemplate, Notification


@admin.register(NotificationTemplate)
class NotificationTemplateAdmin(admin.ModelAdmin):
    """
    Admin interface for NotificationTemplate model.
    """
    list_display = ('name', 'notification_type', 'channel', 'is_active', 'created_at')
    list_filter = ('notification_type', 'channel', 'is_active', 'created_at')
    search_fields = ('name', 'subject', 'message')
    ordering = ['notification_type', 'channel']
    
    fieldsets = (
        (None, {
            'fields': ('name', 'notification_type', 'channel', 'is_active')
        }),
        ('Content', {
            'fields': ('subject', 'message')
        }),
    )


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    """
    Admin interface for Notification model.
    """
    list_display = ('recipient', 'notification_type', 'channel', 'status', 'sent_at', 'created_at')
    list_filter = ('channel', 'status', 'notification_type', 'created_at', 'sent_at')
    search_fields = ('recipient__username', 'recipient__email', 'subject', 'recipient_address')
    ordering = ['-created_at']
    readonly_fields = ('created_at', 'sent_at', 'delivered_at')
    
    fieldsets = (
        (None, {
            'fields': ('recipient', 'channel', 'notification_type', 'status')
        }),
        ('Content', {
            'fields': ('subject', 'message', 'recipient_address')
        }),
        ('Delivery', {
            'fields': ('external_id', 'error_message', 'sent_at', 'delivered_at'),
            'classes': ('collapse',)
        }),
        ('Related Objects', {
            'fields': ('order',),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        return super().get_queryset(request).select_related('recipient', 'order')
