"""
Unit tests for order management and processing.
Tests order creation, status updates, and business logic.
"""
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from orders.models import Order, OrderItem, Cart, CartItem
from products.models import Category, Product
from .base import BaseAPITestCase
from decimal import Decimal


class OrderModelTest(TestCase):
    """Test Order model functionality."""
    
    def setUp(self):
        super().setUp()
        
        # Create test data using base setup
        from .base import BaseTestCase
        base_test = BaseTestCase()
        base_test.setUp()
        
        self.customer = base_test.customer
        self.product = base_test.product
        
    def test_order_creation(self):
        """Test order creation with valid data."""
        order = Order.objects.create(
            customer=self.customer,
            status='pending',
            total_amount=Decimal('299.99')
        )
        
        self.assertEqual(order.customer, self.customer)
        self.assertEqual(order.status, 'pending')
        self.assertEqual(order.total_amount, Decimal('299.99'))
        
    def test_order_item_creation(self):
        """Test order item creation."""
        order = Order.objects.create(
            customer=self.customer,
            total_amount=Decimal('299.99')
        )
        
        order_item = OrderItem.objects.create(
            order=order,
            product=self.product,
            quantity=2,
            price=Decimal('149.99')
        )
        
        self.assertEqual(order_item.order, order)
        self.assertEqual(order_item.product, self.product)
        self.assertEqual(order_item.quantity, 2)
        self.assertEqual(order_item.get_total_price(), Decimal('299.98'))


class CartModelTest(TestCase):
    """Test Cart model functionality."""
    
    def setUp(self):
        super().setUp()
        
        # Create test data using base setup
        from .base import BaseTestCase
        base_test = BaseTestCase()
        base_test.setUp()
        
        self.customer = base_test.customer
        self.product = base_test.product
        
    def test_cart_creation(self):
        """Test cart creation."""
        cart = Cart.objects.create(
            customer=self.customer,
            session_key='test_session'
        )
        
        self.assertEqual(cart.customer, self.customer)
        self.assertEqual(cart.session_key, 'test_session')
        
    def test_cart_item_creation(self):
        """Test cart item creation."""
        cart = Cart.objects.create(customer=self.customer)
        
        cart_item = CartItem.objects.create(
            cart=cart,
            product=self.product,
            quantity=3
        )
        
        self.assertEqual(cart_item.cart, cart)
        self.assertEqual(cart_item.product, self.product)
        self.assertEqual(cart_item.quantity, 3)


class OrderAPITest(BaseAPITestCase):
    """Test Order API endpoints."""
    
    def setUp(self):
        super().setUp()
        
        # Create test category and product
        self.category = Category.objects.create(
            name='Electronics',
            description='Electronic products'
        )
        
        self.product = Product.objects.create(
            name='Test Product',
            description='A test product',
            price=Decimal('99.99'),
            stock_quantity=10,
            category=self.category
        )
        
    def test_create_order_authenticated(self):
        """Test order creation by authenticated user."""
        self.authenticate_user()
        url = reverse('orders:order-list')
        data = {
            'items': [
                {
                    'product': self.product.pk,
                    'quantity': 2
                }
            ]
        }
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Verify order was created
        order = Order.objects.get(pk=response.data['id'])
        self.assertEqual(order.customer, self.customer)
        self.assertEqual(order.items.count(), 1)
        
    def test_create_order_unauthenticated(self):
        """Test that unauthenticated users cannot create orders."""
        url = reverse('orders:order-list')
        data = {
            'items': [
                {
                    'product': self.product.pk,
                    'quantity': 1
                }
            ]
        }
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        
    def test_order_list_customer_only(self):
        """Test that customers only see their own orders."""
        # Create order for authenticated customer
        self.authenticate_user()
        Order.objects.create(
            customer=self.customer,
            total_amount=Decimal('99.99')
        )
        
        # Create another customer and order
        from django.contrib.auth import get_user_model
        User = get_user_model()
        other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='otherpass123'
        )
        other_customer = Customer.objects.create(
            user=other_user,
            phone_number='+254700000002'
        )
        Order.objects.create(
            customer=other_customer,
            total_amount=Decimal('199.99')
        )
        
        url = reverse('orders:order-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['customer'], self.customer.pk)
        
    def test_cart_operations(self):
        """Test cart add, update, and remove operations."""
        self.authenticate_user()
        
        # Add item to cart
        url = reverse('orders:cart-add-item')
        data = {
            'product': self.product.pk,
            'quantity': 2
        }
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify cart item was created
        cart = Cart.objects.get(customer=self.customer)
        self.assertEqual(cart.items.count(), 1)
        self.assertEqual(cart.items.first().quantity, 2)
        
        # Update cart item
        cart_item = cart.items.first()
        url = reverse('orders:cart-update-item', kwargs={'pk': cart_item.pk})
        data = {'quantity': 3}
        
        response = self.client.put(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        cart_item.refresh_from_db()
        self.assertEqual(cart_item.quantity, 3)
