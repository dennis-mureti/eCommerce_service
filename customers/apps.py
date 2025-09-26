"""
Customer app configuration.
"""
from django.apps import AppConfig


class CustomersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'customers'
    
    def ready(self):
        """
        Import signal handlers when app is ready.
        """
        import customers.signals
