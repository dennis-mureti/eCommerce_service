"""
Orders app configuration.
"""
from django.apps import AppConfig


class OrdersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'orders'
    
    def ready(self):
        """
        Import signal handlers when app is ready.
        """
        import orders.signals
