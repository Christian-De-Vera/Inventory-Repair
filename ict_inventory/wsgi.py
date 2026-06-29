"""
WSGI config for ict_inventory project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/wsgi/
"""

import os
import sys

from django.core.wsgi import get_wsgi_application
from django.core.management import call_command

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ict_inventory.settings')

try:
    import django
    django.setup()
    call_command('migrate', '--run-syncdb', verbosity=1)
except Exception as e:
    print(f"Migration error: {e}", file=sys.stderr)

application = get_wsgi_application()
