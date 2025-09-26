"""
Unit tests for notification services.
Tests SMS and email notification functionality.
"""
from django.test import TestCase
from django.core import mail
from unittest.mock import patch, Mock
from notifications.models import NotificationTemplate, NotificationLog
from notifications.services import SMSService, EmailService
from .base import BaseTestCase


class NotificationTemplateTest(TestCase):
    """Test NotificationTemplate model."""
    
    def test_template_creation(self):
        """Test notification template creation."""
        template = NotificationTemplate.objects.create(
            name='order_confirmation',
            template_type='sms',
            subject='Order Confirmation',
            content='Your order #{order_id} has been confirmed.'
        )
        
        self.assertEqual(template.name, 'order_confirmation')
        self.assertEqual(template.template_type, 'sms')
        self.assertTrue(template.is_active)
        
    def test_template_rendering(self):
        """Test template content rendering with context."""
        template = NotificationTemplate.objects.create(
            name='order_confirmation',
            template_type='sms',
            content='Your order #{order_id} for ${total_amount} has been confirmed.'
        )
        
        context = {
            'order_id': '12345',
            'total_amount': '99.99'
        }
        
        rendered = template.render(context)
        expected = 'Your order #12345 for $99.99 has been confirmed.'
        self.assertEqual(rendered, expected)


class SMSServiceTest(TestCase):
    """Test SMS service functionality."""
    
    def setUp(self):
        self.sms_service = SMSService()
        
    @patch('notifications.services.requests.post')
    def test_send_sms_success(self, mock_post):
        """Test successful SMS sending."""
        # Mock successful API response
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            'SMSMessageData': {
                'Recipients': [
                    {
                        'statusCode': 101,
                        'number': '+254700000000',
                        'status': 'Success',
                        'cost': 'KES 0.8000',
                        'messageId': 'ATXid_123456'
                    }
                ]
            }
        }
        mock_post.return_value = mock_response
        
        result = self.sms_service.send_sms(
            phone_number='+254700000000',
            message='Test message'
        )
        
        self.assertTrue(result['success'])
        self.assertEqual(result['message_id'], 'ATXid_123456')
        
    @patch('notifications.services.requests.post')
    def test_send_sms_failure(self, mock_post):
        """Test SMS sending failure."""
        # Mock failed API response
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            'error': 'Invalid phone number'
        }
        mock_post.return_value = mock_response
        
        result = self.sms_service.send_sms(
            phone_number='invalid',
            message='Test message'
        )
        
        self.assertFalse(result['success'])
        self.assertIn('error', result)


class EmailServiceTest(TestCase):
    """Test email service functionality."""
    
    def setUp(self):
        self.email_service = EmailService()
        
    def test_send_email_success(self):
        """Test successful email sending."""
        result = self.email_service.send_email(
            to_email='test@example.com',
            subject='Test Subject',
            message='Test message content'
        )
        
        self.assertTrue(result['success'])
        
        # Check that email was sent
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['test@example.com'])
        self.assertEqual(mail.outbox[0].subject, 'Test Subject')
        
    def test_send_email_with_html(self):
        """Test email sending with HTML content."""
        result = self.email_service.send_email(
            to_email='test@example.com',
            subject='Test Subject',
            message='Plain text content',
            html_message='<h1>HTML Content</h1>'
        )
        
        self.assertTrue(result['success'])
        
        # Check HTML content
        email = mail.outbox[0]
        self.assertEqual(len(email.alternatives), 1)
        self.assertEqual(email.alternatives[0][0], '<h1>HTML Content</h1>')
        self.assertEqual(email.alternatives[0][1], 'text/html')


class NotificationIntegrationTest(BaseTestCase):
    """Test notification integration with orders."""
    
    def setUp(self):
        super().setUp()
        
        # Create notification templates
        self.sms_template = NotificationTemplate.objects.create(
            name='order_confirmation_sms',
            template_type='sms',
            content='Your order #{order_id} has been confirmed. Total: ${total_amount}'
        )
        
        self.email_template = NotificationTemplate.objects.create(
            name='order_notification_email',
            template_type='email',
            subject='New Order Notification',
            content='New order #{order_id} from {customer_name}. Total: ${total_amount}'
        )
        
    @patch('notifications.tasks.send_sms_notification.delay')
    @patch('notifications.tasks.send_email_notification.delay')
    def test_order_notifications_triggered(self, mock_email_task, mock_sms_task):
        """Test that notifications are triggered when order is created."""
        order = self.create_test_order()
        
        # Verify that notification tasks were called
        mock_sms_task.assert_called_once()
        mock_email_task.assert_called_once()
        
        # Check the arguments passed to tasks
        sms_args = mock_sms_task.call_args[1]
        self.assertEqual(sms_args['phone_number'], self.customer.phone_number)
        
        email_args = mock_email_task.call_args[1]
        self.assertIn('admin@', email_args['to_email'])
