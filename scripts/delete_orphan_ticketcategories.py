import os
import sys
import django
# ensure project root on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE','tiktaktuk.settings')
django.setup()
from django.db import connection

with connection.cursor() as c:
    # check table exists
    tables = connection.introspection.table_names()
    if 'events_ticketcategory' not in tables:
        print('events_ticketcategory table not found; nothing to delete')
        print('orphan_count_before: 0')
        print('deleted: 0')
        print('remaining_ticketcategory_rows: 0')
        raise SystemExit(0)

    # count orphan rows
    c.execute("SELECT COUNT(*) FROM events_ticketcategory WHERE event_id NOT IN (SELECT event_id FROM accounts_event)")
    cnt = c.fetchone()[0]
    print('orphan_count_before:', cnt)
    if cnt > 0:
        c.execute("DELETE FROM events_ticketcategory WHERE event_id NOT IN (SELECT event_id FROM accounts_event)")
        print('deleted:', c.rowcount)
    else:
        print('deleted: 0')

    # report remaining sample rows
    c.execute('SELECT COUNT(*) FROM events_ticketcategory')
    remaining = c.fetchone()[0]
    print('remaining_ticketcategory_rows:', remaining)
