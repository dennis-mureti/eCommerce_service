"""
Integration tests for the complete e-commerce workflow.
Tests end-to-end scenarios and system integration.
"""
from django.test import TestCase, TransactionTestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from customers.models import Customer
from products.models import Category, Product
from orders.models import Order, OrderItem
from notifications.models import NotificationLog
from unittest.mock import patch
from decimal import Decimal

User = get_user_model()


class EcommerceWorkflowTest(TransactionTestCase):
    """Test complete e-commerce workflow from registration to order completion."""
    
    def setUp(self):
        self.client = APIClient()
        
        # Create test category and products
        self.electronics = Category.objects.create(
            name='Electronics',
            description='Electronic products'
        )
        
        self.phones = Category.objects.create(
            name='Phones',
            description='Mobile phones',
            parent=self.electronics
        )
        
        self.product1 = Product.objects.create(
            name='iPhone 13',
            description='Apple iPhone 13',
            price=Decimal('999.99'),
            stock_quantity=5,
            category=self.phones
        )
        
        self.product2 = Product.objects.create(
            name='Samsung Galaxy',
            description='Samsung Galaxy phone',
            price=Decimal('799.99'),
            stock_quantity=3,
            category=self.phones
        )
        
    def test_complete_customer_journey(self):
        """Test complete customer journey from registration to order."""
        
        # Step 1: Customer Registration
        register_url = reverse('customers:register')
        register_data = {
            'username': 'testcustomer',
            'email': 'customer@example.com',
            'password': 'testpass123',
            'phone_number': '+254700000000',
            'first_name': 'Test',
            'last_name': 'Customer'
        }
        
        response = self.client.post(register_url, register_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Extract tokens
        access_token = response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        
        # Step 2: Browse Products
        products_url = reverse('products:product-list')
        response = self.client.get(products_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)
        
        # Step 3: Add Items to Cart
        cart_add_url = reverse('orders:cart-add-item')
        
        # Add first product
        cart_data1 = {
            'product': self.product1.pk,
            'quantity': 1
        }
        response = self.client.post(cart_add_url, cart_data1, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Add second product
        cart_data2 = {
            'product': self.product2.pk,
            'quantity': 2
        }
        response = self.client.post(cart_add_url, cart_data2, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Step 4: View Cart
        cart_url = reverse('orders:cart-detail')
        response = self.client.get(cart_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['items']), 2)
        
        # Step 5: Create Order from Cart
        with patch('notifications.tasks.send_sms_notification.delay') as mock_sms, \
             patch('notifications.tasks.send_email_notification.delay') as mock_email:
            
            order_url = reverse('orders:order-list')
            order_data = {
                'items': [
                    {
                        'product': self.product1.pk,
                        'quantity': 1
                    },
                    {
                        'product': self.product2.pk,
                        'quantity': 2
                    }
                ]
            }
            
            response = self.client.post(order_url, order_data, format='json')
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            
            # Verify order details
            order_id = response.data['id']
            order = Order.objects.get(pk=order_id)
            self.assertEqual(order.items.count(), 2)
            
            # Verify notifications were triggered
            mock_sms.assert_called_once()
            mock_email.assert_called_once()
        
        # Step 6: View Order History
        orders_url = reverse('orders:order-list')
        response = self.client.get(orders_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        
        # Step 7: View Order Details
        order_detail_url = reverse('orders:order-detail', kwargs={'pk': order_id})
        response = self.client.get(order_detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], order_id)
        
    def test_category_average_price_calculation(self):
        """Test category average price calculation with hierarchical categories."""
        
        # Test average price for phones category
        avg_url = reverse('products:category-average-price', kwargs={'pk': self.phones.pk})
        response = self.client.get(avg_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Expected average: (999.99 + 799.99) / 2 = 899.99
        expected_avg = (Decimal('999.99') + Decimal('799.99')) / 2
        self.assertEqual(Decimal(str(response.data['average_price'])), expected_avg)
        
        # Test average price for parent category (should include all child products)
        avg_url = reverse('products:category-average-price', kwargs={'pk': self.electronics.pk})
        response = self.client.get(avg_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Should be the same since all products are in the phones subcategory
        self.assertEqual(Decimal(str(response.data['average_price'])), expected_avg)
        
    def test_stock_management(self):
        """Test stock management during order processing."""
        
        # Register and authenticate customer
        register_url = reverse('customers:register')
        register_data = {
            'username': 'stocktest',
            'email': 'stock@example.com',
            'password': 'testpass123',
            'phone_number': '+254700000001'
        }
        
        response = self.client.post(register_url, register_data, format='json')
        access_token = response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        
        # Check initial stock
        initial_stock = self.product1.stock_quantity
        
        # Create order
        order_url = reverse('orders:order-list')
        order_data = {
            'items': [
                {
                    'product': self.product1.pk,
                    'quantity': 2
                }
            ]
        }
        
        with patch('notifications.tasks.send_sms_notification.delay'), \
             patch('notifications.tasks.send_email_notification.delay'):
            
            response = self.client.post(order_url, order_data, format='json')
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Verify stock was reduced
        self.product1.refresh_from_db()
        self.assertEqual(self.product1.stock_quantity, initial_stock - 2)
        
    def test_insufficient_stock_handling(self):
        """Test handling of insufficient stock scenarios."""
        
        # Register and authenticate customer
        register_url = reverse('customers:register')
        register_data = {
            'username': 'stocktest2',
            'email': 'stock2@example.com',
            'password': 'testpass123',
            'phone_number': '+254700000002'
        }
        
        response = self.client.post(register_url, register_data, format='json')
        access_token = response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        
        # Try to order more than available stock
        order_url = reverse('orders:order-list')
        order_data = {
            'items': [
                {
                    'product': self.product1.pk,
                    'quantity': 10  # More than the 5 in stock
                }
            ]
        }
        
        response = self.client.post(order_url, order_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('insufficient stock', str(response.data).lower())
