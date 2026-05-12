#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'supplement_portal.settings')
django.setup()

from accounts.models import User

username = "admin"
email = "admin@provibelife.local"
password = "AdminPass123!"

if not User.objects.filter(username=username).exists():
    User.objects.create_superuser(username, email, password)
    print(f"✓ Superuser created!")
    print(f"  Username: {username}")
    print(f"  Email: {email}")
    print(f"  Password: {password}")
else:
    print(f"User '{username}' already exists")
