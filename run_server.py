#!/usr/bin/env python
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tiktaktuk.settings')
django.setup()

from django.conf import settings
from django.core.management import call_command

# Ensure localhost is allowed
if 'localhost' not in settings.ALLOWED_HOSTS:
    settings.ALLOWED_HOSTS.append('localhost')
if '127.0.0.1' not in settings.ALLOWED_HOSTS:
    settings.ALLOWED_HOSTS.append('127.0.0.1')

if __name__ == '__main__':
    call_command('runserver', '127.0.0.1:8000', verbosity=2)
