from django.apps import AppConfig


class InventoryConfig(AppConfig):
    name = 'inventory'

    def ready(self):
        from django.conf import settings
        if not settings.DEBUG:
            from .keepalive import start_keepalive_thread
            start_keepalive_thread()
