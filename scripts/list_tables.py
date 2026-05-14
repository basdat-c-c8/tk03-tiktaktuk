import os,sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE','tiktaktuk.settings')
import django
django.setup()
from django.db import connection
print('DB file from settings:', connection.settings_dict.get('NAME'))
print('Tables:')
for t in connection.introspection.table_names():
    print('-', t)
