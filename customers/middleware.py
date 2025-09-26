"""
Custom middleware for customer authentication.
"""
import logging
from django.utils.deprecation import MiddlewareMixin
from django.http import JsonResponse
from rest_framework import status

logger = logging.getLogger(__name__)


class AuthenticationLoggingMiddleware(MiddlewareMixin):
    """
    Middleware to log authentication attempts and failures.
    """
    
    def process_request(self, request):
        """
        Log authentication attempts.
        """
        if request.path.startswith('/api/auth/'):
            logger.info(f"Auth request: {request.method} {request.path} from {request.META.get('REMOTE_ADDR', 'unknown')}")
        
        return None
    
    def process_response(self, request, response):
        """
        Log authentication results.
        """
        if request.path.startswith('/api/auth/'):
            if response.status_code >= 400:
                logger.warning(f"Auth failed: {request.method} {request.path} - {response.status_code}")
            else:
                logger.info(f"Auth success: {request.method} {request.path} - {response.status_code}")
        
        return response


class CORSMiddleware(MiddlewareMixin):
    """
    Custom CORS middleware for authentication endpoints.
    """
    
    def process_response(self, request, response):
        """
        Add CORS headers for authentication endpoints.
        """
        if request.path.startswith('/api/'):
            response['Access-Control-Allow-Credentials'] = 'true'
            response['Access-Control-Allow-Headers'] = 'Authorization, Content-Type, X-API-Key'
            response['Access-Control-Allow-Methods'] = 'GET, POST, PUT, PATCH, DELETE, OPTIONS'
        
        return response
