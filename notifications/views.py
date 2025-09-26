"""
Views for notification management API.
"""
from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Count, Q
from django.utils import timezone
from customers.permissions import IsAdminOrReadOnly
from customers.models import Customer
from .models import NotificationTemplate, Notification
from .serializers import (
    NotificationTemplateSerializer, NotificationSerializer,
    SendNotificationSerializer, NotificationStatsSerializer
)
from .services import notification_service
from .tasks import send_notification_async
import logging

logger = logging.getLogger(__name__)


class NotificationTemplateListCreateView(generics.ListCreateAPIView):
    """
    List notification templates or create a new template.
    """
    queryset = NotificationTemplate.objects.all().order_by('notification_type', 'channel')
    serializer_class = NotificationTemplateSerializer
    permission_classes = [permissions.IsAdminUser]
    
    def get_queryset(self):
        """
        Filter templates based on query parameters.
        """
        queryset = super().get_queryset()
        
        notification_type = self.request.query_params.get('type')
        if notification_type:
            queryset = queryset.filter(notification_type=notification_type)
        
        channel = self.request.query_params.get('channel')
        if channel:
            queryset = queryset.filter(channel=channel)
        
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        
        return queryset


class NotificationTemplateDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update or delete a notification template.
    """
    queryset = NotificationTemplate.objects.all()
    serializer_class = NotificationTemplateSerializer
    permission_classes = [permissions.IsAdminUser]


class NotificationListView(generics.ListAPIView):
    """
    List notification records.
    """
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """
        Filter notifications based on user role and parameters.
        """
        user = self.request.user
        
        if user.is_staff:
            queryset = Notification.objects.all()
        else:
            queryset = Notification.objects.filter(recipient=user)
        
        queryset = queryset.select_related('recipient', 'order').order_by('-created_at')
        
        # Apply filters
        channel = self.request.query_params.get('channel')
        if channel:
            queryset = queryset.filter(channel=channel)
        
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        notification_type = self.request.query_params.get('type')
        if notification_type:
            queryset = queryset.filter(notification_type=notification_type)
        
        # Date range filter
        date_from = self.request.query_params.get('date_from')
        if date_from:
            queryset = queryset.filter(created_at__date__gte=date_from)
        
        date_to = self.request.query_params.get('date_to')
        if date_to:
            queryset = queryset.filter(created_at__date__lte=date_to)
        
        return queryset


class SendNotificationView(APIView):
    """
    Send custom notifications to selected recipients.
    """
    permission_classes = [permissions.IsAdminUser]
    
    def post(self, request):
        """
        Send notifications to specified recipients.
        """
        serializer = SendNotificationSerializer(data=request.data)
        if serializer.is_valid():
            data = serializer.validated_data
            
            recipient_ids = data['recipient_ids']
            notification_type = data['notification_type']
            channel = data.get('channel')
            context = data.get('context', {})
            
            # Send notifications asynchronously
            task_results = []
            for recipient_id in recipient_ids:
                task = send_notification_async.delay(
                    recipient_id=recipient_id,
                    notification_type=notification_type,
                    context=context,
                    channel=channel
                )
                task_results.append(task.id)
            
            logger.info(f"Queued {len(task_results)} notifications of type {notification_type}")
            
            return Response({
                'message': f'Queued {len(task_results)} notifications',
                'task_ids': task_results,
                'notification_type': notification_type,
                'recipients': len(recipient_ids)
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([permissions.IsAdminUser])
def test_notification(request):
    """
    Test notification delivery to current user.
    """
    notification_type = request.data.get('notification_type', 'welcome')
    channel = request.data.get('channel')
    
    try:
        result = notification_service.send_notification(
            recipient=request.user,
            notification_type=notification_type,
            context={'test_message': 'This is a test notification'},
            channel=channel
        )
        
        return Response({
            'message': 'Test notification sent',
            'result': result
        })
        
    except Exception as e:
        logger.error(f"Test notification error: {str(e)}")
        return Response({
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([permissions.IsAdminUser])
def notification_stats(request):
    """
    Get notification statistics.
    """
    # Get date range
    date_from = request.query_params.get('date_from')
    date_to = request.query_params.get('date_to')
    
    queryset = Notification.objects.all()
    if date_from:
        queryset = queryset.filter(created_at__date__gte=date_from)
    if date_to:
        queryset = queryset.filter(created_at__date__lte=date_to)
    
    # Calculate statistics
    total_notifications = queryset.count()
    sent_notifications = queryset.filter(status='sent').count()
    failed_notifications = queryset.filter(status='failed').count()
    
    sms_sent = queryset.filter(channel='sms', status='sent').count()
    email_sent = queryset.filter(channel='email', status='sent').count()
    
    success_rate = (sent_notifications / total_notifications * 100) if total_notifications > 0 else 0
    
    # Notifications by type
    notifications_by_type = {}
    type_counts = queryset.values('notification_type').annotate(count=Count('id'))
    for item in type_counts:
        notifications_by_type[item['notification_type']] = item['count']
    
    # Recent notifications
    recent_notifications = queryset.select_related('recipient', 'order').order_by('-created_at')[:10]
    recent_serializer = NotificationSerializer(recent_notifications, many=True)
    
    stats = {
        'total_sent': sent_notifications,
        'total_failed': failed_notifications,
        'sms_sent': sms_sent,
        'email_sent': email_sent,
        'success_rate': round(success_rate, 2),
        'notifications_by_type': notifications_by_type,
        'recent_notifications': recent_serializer.data
    }
    
    return Response(stats)


@api_view(['POST'])
@permission_classes([permissions.IsAdminUser])
def retry_failed_notifications(request):
    """
    Retry failed notifications.
    """
    from .tasks import retry_failed_notifications
    
    task = retry_failed_notifications.delay()
    
    return Response({
        'message': 'Retry task queued',
        'task_id': task.id
    })


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def notification_preferences(request):
    """
    Get notification preferences for authenticated user.
    """
    if not request.user.is_authenticated:
        return Response({
            'error': 'Authentication required'
        }, status=status.HTTP_401_UNAUTHORIZED)
    
    return Response({
        'sms_notifications_enabled': request.user.sms_notifications_enabled,
        'email_notifications_enabled': request.user.email_notifications_enabled,
        'phone_number': request.user.phone_number,
        'email': request.user.email
    })


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def update_notification_preferences(request):
    """
    Update notification preferences for authenticated user.
    """
    user = request.user
    
    sms_enabled = request.data.get('sms_notifications_enabled')
    email_enabled = request.data.get('email_notifications_enabled')
    
    updated_fields = []
    
    if sms_enabled is not None:
        user.sms_notifications_enabled = bool(sms_enabled)
        updated_fields.append('sms_notifications_enabled')
    
    if email_enabled is not None:
        user.email_notifications_enabled = bool(email_enabled)
        updated_fields.append('email_notifications_enabled')
    
    if updated_fields:
        user.save(update_fields=updated_fields)
        logger.info(f"Notification preferences updated for {user.email}")
    
    return Response({
        'message': 'Preferences updated',
        'sms_notifications_enabled': user.sms_notifications_enabled,
        'email_notifications_enabled': user.email_notifications_enabled
    })
