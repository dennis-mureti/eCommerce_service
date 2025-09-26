"""
URL patterns for customer authentication.
"""
from django.urls import path
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from . import views
from .views import (
    CustomerRegistrationView,
    CustomerLoginView,
    OIDCLoginView,
    CustomerLogoutView,
    CustomerProfileView,
    ChangePasswordView,
    OIDCCallbackView,
    customer_orders,
    
)

urlpatterns = [
    # Authentication endpoints
    path('register/', CustomerRegistrationView.as_view(), name='customer-register'),
    path('login/', CustomerLoginView.as_view(), name='customer-login'),
    path('oidc-login/', OIDCLoginView.as_view(), name='oidc-login'),
    # path('oidc/callback/', csrf_exempt(oidc_callback), name='oidc-callback'),
    path('logout/', CustomerLogoutView.as_view(), name='customer-logout'),
    
    # Profile management
    path('profile/', CustomerProfileView.as_view(), name='customer-profile'),
    path('change-password/', ChangePasswordView.as_view(), name='change-password'),
    
    # Customer data
    path('orders/', customer_orders, name='customer-orders'),
    path('oidc/callback/', OIDCCallbackView.as_view(), name='oidc-callback'),

]
