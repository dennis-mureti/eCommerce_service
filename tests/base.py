"""
Base test classes and utilities for the e-commerce API tests.
Follows DRY principles by providing reusable test setup and utilities.
"""
from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase, APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from customers.models import Customer
from products.models import Category, Product
from orders.models import Order, OrderItem
from notifications.models import NotificationTemplate
import json

User = get_user_model()


class BaseTestCase(TestCase):
    """Base test case with common setup and utilities."""
    
    def setUp(self):
        """Set up test data following KISS principles."""
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create test customer
        self.customer = Customer.objects.create(
            user=self.user,
            phone_number='+254700000000',
            date_of_birth='1990-01-01'
        )
        
        # Create test categories (hierarchical)
        self.root_category = Category.objects.create(
            name='Electronics',
            description='Electronic products'
        )
        
        self.sub_category = Category.objects.create(
            name='Smartphones',
            description='Mobile phones',
            parent=self.root_category
        )
        
        # Create test product
        self.product = Product.objects.create(
            name='Test Phone',
            description='A test smartphone',
            price=299.99,
            stock_quantity=10,
            category=self.sub_category
        )
        
    def create_test_order(self, customer=None, status='pending'):
        """Utility method to create test orders."""
        if customer is None:
            customer = self.customer
            
        order = Order.objects.create(
            customer=customer,
            status=status,
            total_amount=299.99
        )
        
        OrderItem.objects.create(
            order=order,
            product=self.product,
            quantity=1,
            price=299.99
        )
        
        return order


class BaseAPITestCase(APITestCase):
    """Base API test case with authentication utilities."""
    
    def setUp(self):
        """Set up API test data."""
        super().setUp()
        
        # Create test user and customer
        self.user = User.objects.create_user(
            username='apiuser',
            email='api@example.com',
            password='apipass123'
        )
        
        self.customer = Customer.objects.create(
            user=self.user,
            phone_number='+254700000001',
            date_of_birth='1990-01-01'
        )
        
        # Create admin user
        self.admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='adminpass123'
        )
        
        self.client = APIClient()
        
    def authenticate_user(self, user=None):
        """Authenticate user for API requests."""
        if user is None:
            user = self.user
            
        refresh = RefreshToken.for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
        
    def authenticate_admin(self):
        """Authenticate admin user for API requests."""
        self.authenticate_user(self.admin_user)
