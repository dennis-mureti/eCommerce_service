"""
Unit tests for customer authentication and management.
Tests OpenID Connect integration and customer CRUD operations.
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from customers.models import Customer
from customers.serializers import CustomerSerializer
from .base import BaseAPITestCase
import json

User = get_user_model()


class CustomerModelTest(TestCase):
    """Test Customer model functionality."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
    def test_customer_creation(self):
        """Test customer creation with valid data."""
        customer = Customer.objects.create(
            user=self.user,
            phone_number='+254700000000',
            date_of_birth='1990-01-01'
        )
        
        self.assertEqual(customer.user, self.user)
        self.assertEqual(customer.phone_number, '+254700000000')
        self.assertTrue(customer.is_active)
        
    def test_customer_str_representation(self):
        """Test customer string representation."""
        customer = Customer.objects.create(
            user=self.user,
            phone_number='+254700000000'
        )
        
        expected = f"{self.user.get_full_name() or self.user.username} - {customer.phone_number}"
        self.assertEqual(str(customer), expected)


class CustomerAPITest(BaseAPITestCase):
    """Test Customer API endpoints."""
    
    def test_customer_registration(self):
        """Test customer registration endpoint."""
        url = reverse('customers:register')
        data = {
            'username': 'newuser',
            'email': 'new@example.com',
            'password': 'newpass123',
            'phone_number': '+254700000002',
            'first_name': 'New',
            'last_name': 'User'
        }
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        
        # Verify user and customer were created
        user = User.objects.get(username='newuser')
        self.assertTrue(Customer.objects.filter(user=user).exists())
        
    def test_customer_login(self):
        """Test customer login endpoint."""
        url = reverse('customers:login')
        data = {
            'username': 'apiuser',
            'password': 'apipass123'
        }
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        
    def test_customer_profile_get(self):
        """Test getting customer profile."""
        self.authenticate_user()
        url = reverse('customers:profile')
        
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['user']['username'], 'apiuser')
        
    def test_customer_profile_update(self):
        """Test updating customer profile."""
        self.authenticate_user()
        url = reverse('customers:profile')
        data = {
            'phone_number': '+254700000999',
            'user': {
                'first_name': 'Updated',
                'last_name': 'Name'
            }
        }
        
        response = self.client.put(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify update
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.phone_number, '+254700000999')
        
    def test_unauthenticated_profile_access(self):
        """Test that unauthenticated users cannot access profile."""
        url = reverse('customers:profile')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
