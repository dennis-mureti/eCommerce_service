"""
Health check endpoints for monitoring and load balancer probes.
"""
from django.http import JsonResponse
from django.db import connections
from django.core.cache import cache
from django.conf import settings
import redis
import time


def health_check(request):
    """
    Basic health check endpoint.
    Returns 200 if the service is running.
    """
    return JsonResponse({
        'status': 'healthy',
        'timestamp': time.time(),
        'service': 'ecommerce-api'
    })


def readiness_check(request):
    """
    Readiness check for Kubernetes.
    Checks database and cache connectivity.
    """
    checks = {}
    overall_status = 'healthy'
    
    # Database check
    try:
        db_conn = connections['default']
        db_conn.cursor()
        checks['database'] = 'healthy'
    except Exception as e:
        checks['database'] = f'unhealthy: {str(e)}'
        overall_status = 'unhealthy'
    
    # Cache check
    try:
        cache.set('health_check', 'test', 10)
        cache.get('health_check')
        checks['cache'] = 'healthy'
    except Exception as e:
        checks['cache'] = f'unhealthy: {str(e)}'
        overall_status = 'unhealthy'
    
    # Redis check (for Celery)
    try:
        redis_client = redis.from_url(settings.CELERY_BROKER_URL)
        redis_client.ping()
        checks['redis'] = 'healthy'
    except Exception as e:
        checks['redis'] = f'unhealthy: {str(e)}'
        overall_status = 'unhealthy'
    
    status_code = 200 if overall_status == 'healthy' else 503
    
    return JsonResponse({
        'status': overall_status,
        'checks': checks,
        'timestamp': time.time()
    }, status=status_code)


def liveness_check(request):
    """
    Liveness check for Kubernetes.
    Simple check to ensure the process is running.
    """
    return JsonResponse({
        'status': 'alive',
        'timestamp': time.time()
    })
