"""
OpenID Connect authentication backend for customer authentication.
"""
import jwt
import requests
from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework import authentication, exceptions
from rest_framework.authentication import BaseAuthentication
from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)
Customer = get_user_model()


class OpenIDConnectAuthentication(BaseAuthentication):
    """
    OpenID Connect JWT token authentication.
    """
    
    def authenticate(self, request):
        """
        Authenticate the request using OpenID Connect JWT token.
        """
        auth_header = request.META.get('HTTP_AUTHORIZATION')
        if not auth_header or not auth_header.startswith('Bearer '):
            return None
        
        token = auth_header.split(' ')[1]
        
        try:
            # Decode and verify the JWT token
            user_info = self.verify_token(token)
            if not user_info:
                return None
            
            # Get or create customer based on OIDC claims
            customer = self.get_or_create_customer(user_info)
            return (customer, token)
            
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid JWT token: {e}")
            raise exceptions.AuthenticationFailed('Invalid token')
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            raise exceptions.AuthenticationFailed('Authentication failed')
    
    def verify_token(self, token):
        """
        Verify JWT token against OpenID Connect provider.
        """
        try:
            # Get OIDC configuration
            oidc_config = self.get_oidc_configuration()
            if not oidc_config:
                return None
            
            # Get public keys for verification
            jwks = self.get_jwks(oidc_config['jwks_uri'])
            if not jwks:
                return None
            
            # Decode token header to get key ID
            unverified_header = jwt.get_unverified_header(token)
            key_id = unverified_header.get('kid')
            
            # Find the correct public key
            public_key = None
            for key in jwks['keys']:
                if key['kid'] == key_id:
                    public_key = jwt.algorithms.RSAAlgorithm.from_jwk(key)
                    break
            
            if not public_key:
                logger.error("Public key not found for token")
                return None
            
            # Verify and decode the token
            payload = jwt.decode(
                token,
                public_key,
                algorithms=['RS256'],
                audience=settings.OIDC_CLIENT_ID,
                issuer=settings.OIDC_ISSUER
            )
            
            return payload
            
        except jwt.ExpiredSignatureError:
            logger.warning("Token has expired")
            return None
        except jwt.InvalidAudienceError:
            logger.warning("Invalid token audience")
            return None
        except jwt.InvalidIssuerError:
            logger.warning("Invalid token issuer")
            return None
        except Exception as e:
            logger.error(f"Token verification error: {e}")
            return None
    
    def get_oidc_configuration(self):
        """
        Get OpenID Connect configuration from provider.
        """
        cache_key = f"oidc_config_{settings.OIDC_ISSUER}"
        config = cache.get(cache_key)
        
        if not config:
            try:
                config_url = f"{settings.OIDC_ISSUER}/.well-known/openid_configuration"
                response = requests.get(config_url, timeout=10)
                response.raise_for_status()
                config = response.json()
                
                # Cache for 1 hour
                cache.set(cache_key, config, 3600)
                
            except Exception as e:
                logger.error(f"Failed to get OIDC configuration: {e}")
                return None
        
        return config
    
    def get_jwks(self, jwks_uri):
        """
        Get JSON Web Key Set from provider.
        """
        cache_key = f"jwks_{jwks_uri}"
        jwks = cache.get(cache_key)
        
        if not jwks:
            try:
                response = requests.get(jwks_uri, timeout=10)
                response.raise_for_status()
                jwks = response.json()
                
                # Cache for 1 hour
                cache.set(cache_key, jwks, 3600)
                
            except Exception as e:
                logger.error(f"Failed to get JWKS: {e}")
                return None
        
        return jwks
    
    def get_or_create_customer(self, user_info):
        """
        Get or create customer based on OIDC user info.
        """
        oidc_sub = user_info.get('sub')
        email = user_info.get('email')
        
        if not oidc_sub or not email:
            raise exceptions.AuthenticationFailed('Invalid user info')
        
        try:
            # Try to find existing customer by OIDC sub
            customer = Customer.objects.get(oidc_sub=oidc_sub)
            
            # Update customer info if needed
            if customer.email != email:
                customer.email = email
                customer.save(update_fields=['email'])
            
            return customer
            
        except Customer.DoesNotExist:
            # Try to find by email and link OIDC
            try:
                customer = Customer.objects.get(email=email)
                customer.oidc_sub = oidc_sub
                customer.oidc_issuer = settings.OIDC_ISSUER
                customer.save(update_fields=['oidc_sub', 'oidc_issuer'])
                return customer
                
            except Customer.DoesNotExist:
                # Create new customer
                customer = Customer.objects.create(
                    username=email,  # Use email as username
                    email=email,
                    first_name=user_info.get('given_name', ''),
                    last_name=user_info.get('family_name', ''),
                    oidc_sub=oidc_sub,
                    oidc_issuer=settings.OIDC_ISSUER,
                    is_active=True
                )
                
                logger.info(f"Created new customer: {customer.email}")
                return customer


class APIKeyAuthentication(BaseAuthentication):
    """
    Simple API key authentication for admin operations.
    """
    
    def authenticate(self, request):
        """
        Authenticate using API key in header.
        """
        api_key = request.META.get('HTTP_X_API_KEY')
        if not api_key:
            return None
        
        # For demo purposes, use a simple API key check
        # In production, store API keys securely in database
        admin_api_key = getattr(settings, 'ADMIN_API_KEY', None)
        if api_key == admin_api_key:
            # Return a special admin user
            try:
                admin_user = Customer.objects.get(is_superuser=True, is_staff=True)
                return (admin_user, api_key)
            except Customer.DoesNotExist:
                pass
        
        return None
