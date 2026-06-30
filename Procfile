release: python manage.py collectstatic --noinput
web: gunicorn ict_inventory.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --threads 4
