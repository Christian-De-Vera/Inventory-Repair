"""
WSGI config for ict_inventory project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/wsgi/
"""

import os
import sys
from pathlib import Path

from django.core.wsgi import get_wsgi_application
from django.core.management import call_command

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ict_inventory.settings')

try:
    import django
    django.setup()
    call_command('migrate', '--run-syncdb', verbosity=1)
    # Ensure media directory exists
    from django.conf import settings
    if not os.path.exists(settings.MEDIA_ROOT):
        os.makedirs(settings.MEDIA_ROOT, exist_ok=True)
except Exception as e:
    print(f"Migration error: {e}", file=sys.stderr)

application = get_wsgi_application()

# Configure WhiteNoise to serve static files in production
if os.environ.get('DJANGO_DEBUG', 'False') != 'True':
    from whitenoise import WhiteNoise
    static_root = Path(__file__).resolve().parent.parent / 'staticfiles'
    if static_root.exists():
        application = WhiteNoise(application, root=str(static_root), prefix='/static/')
    else:
        # Fallback: use Django's staticfiles finders to find static files
        import warnings
        warnings.warn(f"Staticfiles directory not found at {static_root}. Run collectstatic during deployment.")