"""
URL patterns for notification management API.
"""
from django.urls import path
from .views import (
    NotificationTemplateListCreateView, NotificationTemplateDetailView,
    NotificationListView, SendNotificationView, test_notification,
    notification_stats, retry_failed_notifications,
    notification_preferences, update_notification_preferences
)

urlpatterns = [
    # Template management
    path('templates/', NotificationTemplateListCreateView.as_view(), name='notification-template-list-create'),
    path('templates/<int:pk>/', NotificationTemplateDetailView.as_view(), name='notification-template-detail'),
    
    # Notification records
    path('', NotificationListView.as_view(), name='notification-list'),
    path('send/', SendNotificationView.as_view(), name='send-notification'),
    path('test/', test_notification, name='test-notification'),
    
    # Statistics and management
    path('stats/', notification_stats, name='notification-stats'),
    path('retry-failed/', retry_failed_notifications, name='retry-failed-notifications'),
    
    # User preferences
    path('preferences/', notification_preferences, name='notification-preferences'),
    path('preferences/update/', update_notification_preferences, name='update-notification-preferences'),
]
