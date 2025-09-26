"""
Views for customer authentication and management.
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework import permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.generics import RetrieveUpdateAPIView
from rest_framework.authtoken.models import Token
from django.contrib.auth import login, logout
from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver
from django.shortcuts import redirect
from django.conf import settings
from urllib.parse import urlencode
import requests
import logging

from .models import Customer
from .serializers import (
    CustomerRegistrationSerializer,
    CustomerLoginSerializer,
    CustomerProfileSerializer,
    ChangePasswordSerializer,
    OIDCTokenSerializer
)
from .authentication import OpenIDConnectAuthentication
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

logger = logging.getLogger(__name__)

class CustomerRegistrationView(APIView):
    """
    Customer registration endpoint.
    """
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        """
        Register a new customer.
        """
        serializer = CustomerRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            customer = serializer.save()
            
            # Create auth token
            token, created = Token.objects.get_or_create(user=customer)
            
            # Return customer data with token
            profile_serializer = CustomerProfileSerializer(customer)
            
            logger.info(f"New customer registered: {customer.email}")
            
            return Response({
                'customer': profile_serializer.data,
                'token': token.key,
                'message': 'Registration successful'
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class CustomerLoginView(APIView):
    """
    Customer login endpoint.
    """
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        """
        Authenticate customer and return token.
        """
        serializer = CustomerLoginSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if serializer.is_valid():
            customer = serializer.validated_data['customer']
            
            # Create or get auth token
            token, created = Token.objects.get_or_create(user=customer)
            
            # Log the user in
            login(request, customer)
            
            # Return customer data with token
            profile_serializer = CustomerProfileSerializer(customer)
            
            logger.info(f"Customer logged in: {customer.email}")
            
            return Response({
                'customer': profile_serializer.data,
                'token': token.key,
                'message': 'Login successful'
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class OIDCLoginView(APIView):
    """
    OpenID Connect login endpoint.
    """
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def get(self, request):
        """ 
        Initiate OIDC login flow by redirecting to the OIDC provider.
        """
        from urllib.parse import urlencode
        
        # Build the authorization URL
        auth_params = {
            'response_type': 'code',
            'client_id': settings.OIDC_CLIENT_ID,
            'redirect_uri': settings.OIDC_REDIRECT_URI,
            'scope': 'openid email profile',
            'access_type': 'offline',
            'prompt': 'consent',
        }
        
        auth_url = f"{settings.OIDC_AUTH_URL}?{urlencode(auth_params)}"
        return redirect(auth_url)
    
    
    def post(self, request):
        """
        Authenticate using OpenID Connect ID token.
        """
        serializer = OIDCTokenSerializer(data=request.data)
        if serializer.is_valid():
            id_token = serializer.validated_data['id_token']
            
            # Use OIDC authentication to verify token and get customer
            auth = OpenIDConnectAuthentication()
            
            # Temporarily set the token in request for authentication
            request.META['HTTP_AUTHORIZATION'] = f'Bearer {id_token}'
            
            try:
                auth_result = auth.authenticate(request)
                if auth_result:
                    customer, token = auth_result
                    
                    # Create Django auth token for API access
                    api_token, created = Token.objects.get_or_create(user=customer)
                    
                    # Log the user in
                    login(request, customer)
                    
                    # Return customer data with token
                    profile_serializer = CustomerProfileSerializer(customer)
                    
                    logger.info(f"Customer logged in via OIDC: {customer.email}")
                    
                    return Response({
                        'customer': profile_serializer.data,
                        'token': api_token.key,
                        'message': 'OIDC login successful'
                    })
                else:
                    return Response({
                        'error': 'Invalid ID token'
                    }, status=status.HTTP_401_UNAUTHORIZED)
                    
            except Exception as e:
                logger.error(f"OIDC login error: {e}")
                return Response({
                    'error': 'Authentication failed'
                }, status=status.HTTP_401_UNAUTHORIZED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

def oidc_callback(request):
    """
    Handle the OIDC callback from the identity provider.
    """
    # Check for error in callback
    if 'error' in request.GET:
        error = request.GET.get('error')
        error_desc = request.GET.get('error_description', 'No error description')
        logger.error(f"OIDC error: {error} - {error_desc}")
        return Response(
            {'error': 'Authentication failed'}, 
            status=status.HTTP_401_UNAUTHORIZED
        )
    
    # Get the authorization code
    code = request.GET.get('code')
    if not code:
        logger.error("No authorization code received in OIDC callback")
        return Response(
            {'error': 'Missing authorization code'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        # Exchange authorization code for tokens
        token_url = 'https://oauth2.googleapis.com/token'
        token_data = {
            'code': code,
            'client_id': settings.OIDC_CLIENT_ID,
            'client_secret': settings.OIDC_CLIENT_SECRET,
            'redirect_uri': 'http://localhost:8000/api/auth/oidc/callback/',
            'grant_type': 'authorization_code'
        }
        
        response = requests.post(
            token_url,
            data=token_data,
            headers={'Content-Type': 'application/x-www-form-urlencoded'}
        )
        response.raise_for_status()
        
        token_response = response.json()
        id_token = token_response.get('id_token')
        
        if not id_token:
            logger.error("No ID token in OIDC token response")
            return Response(
                {'error': 'Authentication failed - no ID token'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # Now call the OIDC login endpoint with the ID token
        login_url = 'http://localhost:8000/api/auth/oidc-login/'
        login_response = requests.post(
            login_url,
            json={'id_token': id_token},
            headers={'Content-Type': 'application/json'}
        )
        
        if login_response.status_code == 200:
            # Redirect to frontend with the token
            frontend_url = 'http://localhost:3000/oidc/callback'
            token_data = login_response.json()
            token = token_data.get('token')
            if token:
                return redirect(f"{frontend_url}?token={token}")
        
        # If we get here, something went wrong
        logger.error(f"OIDC login failed: {login_response.text}")
        return Response(
            {'error': 'Authentication failed'}, 
            status=status.HTTP_401_UNAUTHORIZED
        )
        
    except requests.exceptions.RequestException as e:
        logger.error(f"OIDC token exchange error: {str(e)}")
        return Response(
            {'error': 'Authentication service unavailable'}, 
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )
    except Exception as e:
        logger.error(f"Unexpected error in OIDC callback: {str(e)}", exc_info=True)
        return Response(
            {'error': 'Internal server error'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

class CustomerLogoutView(APIView):
    """
    Customer logout endpoint.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        """
        Logout customer and delete token.
        """
        try:
            # Delete the auth token
            Token.objects.filter(user=request.user).delete()
            
            # Logout the user
            logout(request)
            
            logger.info(f"Customer logged out: {request.user.email}")
            
            return Response({
                'message': 'Logout successful'
            })
        except Exception as e:
            logger.error(f"Logout error: {e}")
            return Response({
                'error': 'Logout failed'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class CustomerProfileView(RetrieveUpdateAPIView):
    """
    Customer profile management endpoint.
    """
    serializer_class = CustomerProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        """
        Return the current authenticated customer.
        """
        return self.request.user

class ChangePasswordView(APIView):
    """
    Password change endpoint.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        """
        Change customer password.
        """
        serializer = ChangePasswordSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if serializer.is_valid():
            serializer.save()
            
            # Delete existing tokens to force re-authentication
            Token.objects.filter(user=request.user).delete()
            
            logger.info(f"Password changed for customer: {request.user.email}")
            
            return Response({
                'message': 'Password changed successfully. Please login again.'
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def customer_orders(request):
    """
    Get customer's order history.
    """
    orders = request.user.orders.all().order_by('-created_at')
    
    # Simple order data - will be enhanced when we build the order API
    order_data = []
    for order in orders:
        order_data.append({
            'id': order.id,
            'order_number': order.order_number,
            'status': order.status,
            'total_amount': str(order.total_amount),
            'created_at': order.created_at,
            'items_count': order.total_items
        })
    
    return Response({
        'orders': order_data,
        'count': len(order_data)
    })


class OIDCCallbackView(APIView):
    """
    Handle the OIDC callback from the identity provider.
    """
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def get(self, request):
        logger.info("OIDC callback received")
        
        # Check for error in callback
        if 'error' in request.GET:
            error = request.GET.get('error')
            error_desc = request.GET.get('error_description', 'No error description')
            logger.error(f"OIDC error: {error} - {error_desc}")
            return Response(
                {'error': 'Authentication failed'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # Get the authorization code
        code = request.GET.get('code')
        if not code:
            logger.error("No authorization code received in OIDC callback")
            return Response(
                {'error': 'Missing authorization code'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            logger.info("Exchanging authorization code for tokens...")
            # Exchange authorization code for tokens
            token_data = {
                'code': code,
                'client_id': settings.OIDC_CLIENT_ID,
                'client_secret': settings.OIDC_CLIENT_SECRET,
                'redirect_uri': settings.OIDC_REDIRECT_URI.rstrip('/'),
                'grant_type': 'authorization_code'
            }
            
            logger.debug(f"Token request data: {token_data}")
            token_url = 'https://oauth2.googleapis.com/token'
            
            response = requests.post(
                token_url,
                data=token_data,
                headers={'Content-Type': 'application/x-www-form-urlencoded',
                'Accept': 'application/json'}
            )
            
            logger.debug(f"Token response status: {response.status_code}")
            logger.debug(f"Token response: {response.text}")
            
            response.raise_for_status()
            
            token_response = response.json()
            id_token = token_response.get('id_token')
            
            if not id_token:
                logger.error("No ID token in OIDC token response")
                return Response(
                    {'error': 'Authentication failed - no ID token'}, 
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            logger.info("ID token received, authenticating...")
            
            # Now call the OIDC login endpoint with the ID token
            login_url = request.build_absolute_uri('/api/auth/oidc-login/')
            login_response = requests.post(
                login_url, 
                json={'id_token': id_token},
                headers={'Content-Type': 'application/json'}
            )
            
            logger.debug(f"Login response status: {login_response.status_code}")
            logger.debug(f"Login response: {login_response.text}")
            
            if login_response.status_code == 200:
                # Redirect to frontend with the token
                frontend_url = 'http://localhost:3000/oidc/callback'
                token_data = login_response.json()
                token = token_data.get('token')
                if token:
                    logger.info("Authentication successful, redirecting to frontend")
                    return redirect(f"{frontend_url}?token={token}")
            
            # If we get here, something went wrong
            logger.error(f"OIDC login failed: {login_response.text}")
            return Response(
                {'error': 'Authentication failed'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
            
        except requests.exceptions.RequestException as e:
            logger.error(f"OIDC token exchange error: {str(e)}")
            return Response(
                {'error': 'Authentication service unavailable'}, 
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        except Exception as e:
            logger.error(f"Unexpected error in OIDC callback: {str(e)}", exc_info=True)
            return Response(
                {'error': 'Internal server error'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    """
    Log successful user logins.
    """
    logger.info(f"User login: {user.email} from {request.META.get('REMOTE_ADDR', 'unknown')}")