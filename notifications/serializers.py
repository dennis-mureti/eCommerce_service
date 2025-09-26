"""
Serializers for notification management API.
"""
from rest_framework import serializers
from .models import NotificationTemplate, Notification


class NotificationTemplateSerializer(serializers.ModelSerializer):
    """
    Serializer for notification templates.
    """
    class Meta:
        model = NotificationTemplate
        fields = [
            'id', 'name', 'notification_type', 'channel', 'subject',
            'message', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def validate(self, attrs):
        """
        Validate template uniqueness.
        """
        notification_type = attrs.get('notification_type')
        channel = attrs.get('channel')
        
        # Check for existing template with same type and channel
        queryset = NotificationTemplate.objects.filter(
            notification_type=notification_type,
            channel=channel
        )
        
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)
        
        if queryset.exists():
            raise serializers.ValidationError(
                f"Template for {notification_type} via {channel} already exists."
            )
        
        return attrs


class NotificationSerializer(serializers.ModelSerializer):
    """
    Serializer for notification records.
    """
    recipient_name = serializers.CharField(source='recipient.full_name', read_only=True)
    order_number = serializers.CharField(source='order.order_number', read_only=True)
    
    class Meta:
        model = Notification
        fields = [
            'id', 'recipient', 'recipient_name', 'channel', 'notification_type',
            'subject', 'message', 'recipient_address', 'status', 'order',
            'order_number', 'external_id', 'error_message', 'sent_at',
            'delivered_at', 'created_at'
        ]
        read_only_fields = [
            'id', 'external_id', 'sent_at', 'delivered_at', 'created_at'
        ]


class SendNotificationSerializer(serializers.Serializer):
    """
    Serializer for sending custom notifications.
    """
    recipient_ids = serializers.ListField(
        child=serializers.IntegerField(),
        min_length=1,
        max_length=100
    )
    notification_type = serializers.ChoiceField(
        choices=NotificationTemplate.NOTIFICATION_TYPES
    )
    channel = serializers.ChoiceField(
        choices=NotificationTemplate.CHANNEL_CHOICES,
        required=False
    )
    context = serializers.DictField(required=False)
    
    def validate_recipient_ids(self, value):
        """
        Validate that all recipients exist.
        """
        from customers.models import Customer
        
        existing_ids = Customer.objects.filter(
            id__in=value,
            is_active=True
        ).values_list('id', flat=True)
        
        missing_ids = set(value) - set(existing_ids)
        if missing_ids:
            raise serializers.ValidationError(
                f"Recipients not found: {list(missing_ids)}"
            )
        
        return value


class NotificationStatsSerializer(serializers.Serializer):
    """
    Serializer for notification statistics.
    """
    total_sent = serializers.IntegerField()
    total_failed = serializers.IntegerField()
    sms_sent = serializers.IntegerField()
    email_sent = serializers.IntegerField()
    success_rate = serializers.FloatField()
    notifications_by_type = serializers.DictField()
    recent_notifications = NotificationSerializer(many=True)
