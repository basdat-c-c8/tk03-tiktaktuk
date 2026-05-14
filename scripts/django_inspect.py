import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE','tiktaktuk.settings')
django.setup()
from accounts.models import Event
from django.db import connection
print('Event count:', Event.objects.count())
print('Events sample:', list(Event.objects.values('event_id','event_title')[:20]))
with connection.cursor() as c:
    c.execute('SELECT category_id, category_name, event_id FROM events_ticketcategory')
    rows = c.fetchall()
    print('TicketCategory rows count:', len(rows))
    for r in rows[:20]:
        print(r)
