#!/usr/bin/env python
# django_shell.py

from django.core.management import call_command
from boot_django import boot_django, APP_NAME  # noqa


boot_django()
print(f'checking migrations for {APP_NAME}')
call_command('makemigrations', APP_NAME, '--check')
