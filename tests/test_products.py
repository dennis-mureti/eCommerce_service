"""
Unit tests for product management and category hierarchy.
Tests hierarchical categories and product CRUD operations.
"""
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from products.models import Category, Product
from .base import BaseAPITestCase
from decimal import Decimal


class CategoryModelTest(TestCase):
    """Test Category model functionality."""
    
    def test_category_hierarchy(self):
        """Test hierarchical category structure."""
        # Create root category
        electronics = Category.objects.create(
            name='Electronics',
            description='Electronic products'
        )
        
        # Create subcategory
        phones = Category.objects.create(
            name='Phones',
            description='Mobile phones',
            parent=electronics
        )
        
        # Create sub-subcategory
        smartphones = Category.objects.create(
            name='Smartphones',
            description='Smart mobile phones',
            parent=phones
        )
        
        # Test hierarchy
        self.assertEqual(electronics.get_level(), 0)
        self.assertEqual(phones.get_level(), 1)
        self.assertEqual(smartphones.get_level(), 2)
        
        # Test children
        self.assertIn(phones, electronics.get_children())
        self.assertIn(smartphones, phones.get_children())
        
    def test_category_str_representation(self):
        """Test category string representation."""
        category = Category.objects.create(name='Test Category')
        self.assertEqual(str(category), 'Test Category')


class ProductModelTest(TestCase):
    """Test Product model functionality."""
    
    def setUp(self):
        self.category = Category.objects.create(
            name='Test Category',
            description='Test category'
        )
        
    def test_product_creation(self):
        """Test product creation with valid data."""
        product = Product.objects.create(
            name='Test Product',
            description='A test product',
            price=Decimal('99.99'),
            stock_quantity=10,
            category=self.category
        )
        
        self.assertEqual(product.name, 'Test Product')
        self.assertEqual(product.price, Decimal('99.99'))
        self.assertEqual(product.stock_quantity, 10)
        self.assertTrue(product.is_active)
        
    def test_product_in_stock(self):
        """Test product stock checking."""
        product = Product.objects.create(
            name='Test Product',
            price=Decimal('99.99'),
            stock_quantity=5,
            category=self.category
        )
        
        self.assertTrue(product.is_in_stock())
        
        # Test out of stock
        product.stock_quantity = 0
        product.save()
        self.assertFalse(product.is_in_stock())


class ProductAPITest(BaseAPITestCase):
    """Test Product API endpoints."""
    
    def setUp(self):
        super().setUp()
        
        # Create test categories
        self.electronics = Category.objects.create(
            name='Electronics',
            description='Electronic products'
        )
        
        self.phones = Category.objects.create(
            name='Phones',
            description='Mobile phones',
            parent=self.electronics
        )
        
        # Create test products
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
        
    def test_product_list(self):
        """Test product listing endpoint."""
        url = reverse('products:product-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)
        
    def test_product_detail(self):
        """Test product detail endpoint."""
        url = reverse('products:product-detail', kwargs={'pk': self.product1.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'iPhone 13')
        
    def test_product_create_admin_required(self):
        """Test that product creation requires admin permissions."""
        self.authenticate_user()  # Regular user
        url = reverse('products:product-list')
        data = {
            'name': 'New Product',
            'description': 'A new product',
            'price': '199.99',
            'stock_quantity': 10,
            'category': self.phones.pk
        }
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
    def test_product_create_admin_success(self):
        """Test successful product creation by admin."""
        self.authenticate_admin()
        url = reverse('products:product-list')
        data = {
            'name': 'New Product',
            'description': 'A new product',
            'price': '199.99',
            'stock_quantity': 10,
            'category': self.phones.pk
        }
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'New Product')
        
    def test_category_average_price(self):
        """Test category average price calculation."""
        url = reverse('products:category-average-price', kwargs={'pk': self.phones.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Calculate expected average: (999.99 + 799.99) / 2 = 899.99
        expected_avg = (Decimal('999.99') + Decimal('799.99')) / 2
        self.assertEqual(Decimal(str(response.data['average_price'])), expected_avg)
        
    def test_product_search(self):
        """Test product search functionality."""
        url = reverse('products:product-list')
        response = self.client.get(url, {'search': 'iPhone'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['name'], 'iPhone 13')
