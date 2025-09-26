"""
Notification services for SMS and email delivery.
"""
import africastalking
import requests
from django.conf import settings
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from .models import Notification, NotificationTemplate
import logging

logger = logging.getLogger(__name__)


class SMSService:
    """
    SMS service using Africa's Talking API.
    """
    
    def __init__(self):
        """
        Initialize Africa's Talking SDK.
        """
        if settings.AFRICASTALKING_USERNAME and settings.AFRICASTALKING_API_KEY:
            africastalking.initialize(
                settings.AFRICASTALKING_USERNAME,
                settings.AFRICASTALKING_API_KEY
            )
            self.sms = africastalking.SMS
            self.enabled = True
        else:
            logger.warning("Africa's Talking credentials not configured")
            self.enabled = False
    
    def send_sms(self, phone_number, message, notification_id=None):
        """
        Send SMS message.
        
        Args:
            phone_number (str): Recipient phone number
            message (str): SMS message content
            notification_id (int): Notification record ID
            
        Returns:
            dict: Response with success status and message ID
        """
        if not self.enabled:
            logger.error("SMS service not enabled")
            return {'success': False, 'error': 'SMS service not configured'}
        
        try:
            # Ensure phone number is in correct format
            if not phone_number.startswith('+'):
                # Assume Kenyan number if no country code
                if phone_number.startswith('0'):
                    phone_number = '+254' + phone_number[1:]
                elif phone_number.startswith('7') or phone_number.startswith('1'):
                    phone_number = '+254' + phone_number
            
            # Send SMS
            response = self.sms.send(message, [phone_number])
            
            if response['SMSMessageData']['Recipients']:
                recipient = response['SMSMessageData']['Recipients'][0]
                
                if recipient['status'] == 'Success':
                    logger.info(f"SMS sent successfully to {phone_number}")
                    
                    # Update notification record
                    if notification_id:
                        try:
                            notification = Notification.objects.get(id=notification_id)
                            notification.status = 'sent'
                            notification.external_id = recipient.get('messageId', '')
                            notification.sent_at = timezone.now()
                            notification.save()
                        except Notification.DoesNotExist:
                            pass
                    
                    return {
                        'success': True,
                        'message_id': recipient.get('messageId', ''),
                        'cost': recipient.get('cost', '')
                    }
                else:
                    error_msg = recipient.get('status', 'Unknown error')
                    logger.error(f"SMS failed to {phone_number}: {error_msg}")
                    
                    # Update notification record
                    if notification_id:
                        try:
                            notification = Notification.objects.get(id=notification_id)
                            notification.status = 'failed'
                            notification.error_message = error_msg
                            notification.save()
                        except Notification.DoesNotExist:
                            pass
                    
                    return {'success': False, 'error': error_msg}
            else:
                logger.error(f"No recipients in SMS response for {phone_number}")
                return {'success': False, 'error': 'No recipients in response'}
                
        except Exception as e:
            logger.error(f"SMS sending error: {str(e)}")
            
            # Update notification record
            if notification_id:
                try:
                    notification = Notification.objects.get(id=notification_id)
                    notification.status = 'failed'
                    notification.error_message = str(e)
                    notification.save()
                except Notification.DoesNotExist:
                    pass
            
            return {'success': False, 'error': str(e)}


class EmailService:
    """
    Email service for sending notifications.
    """
    
    def send_email(self, recipient_email, subject, message, html_message=None, notification_id=None):
        """
        Send email message.
        
        Args:
            recipient_email (str): Recipient email address
            subject (str): Email subject
            message (str): Plain text message
            html_message (str): HTML message (optional)
            notification_id (int): Notification record ID
            
        Returns:
            dict: Response with success status
        """
        try:
            if html_message:
                # Send HTML email
                email = EmailMultiAlternatives(
                    subject=subject,
                    body=message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[recipient_email]
                )
                email.attach_alternative(html_message, "text/html")
                email.send()
            else:
                # Send plain text email
                send_mail(
                    subject=subject,
                    message=message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[recipient_email],
                    fail_silently=False
                )
            
            logger.info(f"Email sent successfully to {recipient_email}")
            
            # Update notification record
            if notification_id:
                try:
                    notification = Notification.objects.get(id=notification_id)
                    notification.status = 'sent'
                    notification.sent_at = timezone.now()
                    notification.save()
                except Notification.DoesNotExist:
                    pass
            
            return {'success': True}
            
        except Exception as e:
            logger.error(f"Email sending error: {str(e)}")
            
            # Update notification record
            if notification_id:
                try:
                    notification = Notification.objects.get(id=notification_id)
                    notification.status = 'failed'
                    notification.error_message = str(e)
                    notification.save()
                except Notification.DoesNotExist:
                    pass
            
            return {'success': False, 'error': str(e)}


class NotificationService:
    """
    Main notification service that handles template rendering and delivery.
    """
    
    def __init__(self):
        self.sms_service = SMSService()
        self.email_service = EmailService()
    
    def render_template(self, template, context):
        """
        Render notification template with context data.
        
        Args:
            template (NotificationTemplate): Template instance
            context (dict): Template context data
            
        Returns:
            dict: Rendered subject and message
        """
        try:
            # Simple template variable replacement
            subject = template.subject
            message = template.message
            
            for key, value in context.items():
                placeholder = f"{{{{{key}}}}}"
                subject = subject.replace(placeholder, str(value))
                message = message.replace(placeholder, str(value))
            
            return {
                'subject': subject,
                'message': message
            }
            
        except Exception as e:
            logger.error(f"Template rendering error: {str(e)}")
            return {
                'subject': template.subject,
                'message': template.message
            }
    
    def send_notification(self, recipient, notification_type, context=None, channel=None):
        """
        Send notification using appropriate template and channel.
        
        Args:
            recipient (Customer): Notification recipient
            notification_type (str): Type of notification
            context (dict): Template context data
            channel (str): Notification channel ('sms', 'email', or None for both)
            
        Returns:
            dict: Delivery results
        """
        if context is None:
            context = {}
        
        # Add recipient data to context
        context.update({
            'customer_name': recipient.full_name or recipient.username,
            'customer_email': recipient.email,
            'customer_phone': recipient.phone_number
        })
        
        results = {'sms': None, 'email': None}
        
        # Determine channels to use
        channels = []
        if channel:
            channels = [channel]
        else:
            if recipient.sms_notifications_enabled and recipient.phone_number:
                channels.append('sms')
            if recipient.email_notifications_enabled and recipient.email:
                channels.append('email')
        
        # Send notifications
        for ch in channels:
            try:
                template = NotificationTemplate.objects.get(
                    notification_type=notification_type,
                    channel=ch,
                    is_active=True
                )
                
                rendered = self.render_template(template, context)
                
                # Create notification record
                notification = Notification.objects.create(
                    recipient=recipient,
                    channel=ch,
                    notification_type=notification_type,
                    subject=rendered['subject'],
                    message=rendered['message'],
                    recipient_address=recipient.phone_number if ch == 'sms' else recipient.email,
                    order=context.get('order')
                )
                
                # Send notification
                if ch == 'sms':
                    result = self.sms_service.send_sms(
                        recipient.phone_number,
                        rendered['message'],
                        notification.id
                    )
                    results['sms'] = result
                    
                elif ch == 'email':
                    result = self.email_service.send_email(
                        recipient.email,
                        rendered['subject'],
                        rendered['message'],
                        notification_id=notification.id
                    )
                    results['email'] = result
                
            except NotificationTemplate.DoesNotExist:
                logger.warning(f"No template found for {notification_type} via {ch}")
                results[ch] = {'success': False, 'error': 'Template not found'}
            except Exception as e:
                logger.error(f"Notification sending error: {str(e)}")
                results[ch] = {'success': False, 'error': str(e)}
        
        return results
    
    def send_order_confirmation(self, order):
        """
        Send order confirmation notification.
        """
        context = {
            'order_number': order.order_number,
            'order_total': str(order.total_amount),
            'order_items': order.total_items,
            'order_date': order.created_at.strftime('%Y-%m-%d %H:%M'),
            'order': order
        }
        
        return self.send_notification(
            recipient=order.customer,
            notification_type='order_confirmation',
            context=context
        )
    
    def send_order_shipped(self, order):
        """
        Send order shipped notification.
        """
        context = {
            'order_number': order.order_number,
            'order_total': str(order.total_amount),
            'shipping_address': order.shipping_address,
            'order': order
        }
        
        return self.send_notification(
            recipient=order.customer,
            notification_type='order_shipped',
            context=context
        )
    
    def send_order_delivered(self, order):
        """
        Send order delivered notification.
        """
        context = {
            'order_number': order.order_number,
            'order_total': str(order.total_amount),
            'order': order
        }
        
        return self.send_notification(
            recipient=order.customer,
            notification_type='order_delivered',
            context=context
        )
    
    def send_order_cancelled(self, order):
        """
        Send order cancelled notification.
        """
        context = {
            'order_number': order.order_number,
            'order_total': str(order.total_amount),
            'order': order
        }
        
        return self.send_notification(
            recipient=order.customer,
            notification_type='order_cancelled',
            context=context
        )
    
    def send_welcome_message(self, customer):
        """
        Send welcome message to new customer.
        """
        context = {
            'customer': customer
        }
        
        return self.send_notification(
            recipient=customer,
            notification_type='welcome',
            context=context
        )
    
    def send_low_stock_alert(self, product, admin_users):
        """
        Send low stock alert to administrators.
        """
        context = {
            'product_name': product.name,
            'product_sku': product.sku,
            'stock_quantity': product.stock_quantity,
            'low_stock_threshold': product.low_stock_threshold
        }
        
        results = []
        for admin in admin_users:
            result = self.send_notification(
                recipient=admin,
                notification_type='low_stock_alert',
                context=context,
                channel='email'  # Admin alerts via email only
            )
            results.append(result)
        
        return results


# Global notification service instance
notification_service = NotificationService()
