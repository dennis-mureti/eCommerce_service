"""
URL patterns for order management API.
"""
from django.urls import path
from .views import (
    OrderListCreateView, OrderDetailView, CartView,
    cancel_order, remove_cart_item, order_analytics,
    customer_order_history
)

urlpatterns = [
    # Order endpoints
    path('', OrderListCreateView.as_view(), name='order-list-create'),
    path('<str:order_number>/', OrderDetailView.as_view(), name='order-detail'),
    path('<str:order_number>/cancel/', cancel_order, name='cancel-order'),
    
    # Cart endpoints
    path('cart/', CartView.as_view(), name='cart'),
    path('cart/items/<int:product_id>/', remove_cart_item, name='remove-cart-item'),
    
    # Analytics and history
    path('analytics/', order_analytics, name='order-analytics'),
    path('history/', customer_order_history, name='customer-order-history'),
]
