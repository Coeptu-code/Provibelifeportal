web: python manage.py migrate --noinput && gunicorn supplement_portal.wsgi:application --bind 0.0.0.0:$PORT --workers 3 --timeout 120
