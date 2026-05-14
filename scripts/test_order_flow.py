from django.conf import settings
settings.ALLOWED_HOSTS = ['testserver', 'localhost', '127.0.0.1']
from django.contrib.auth.models import User
from django.test import Client
from django.utils import timezone

from accounts.models import Customer, Organizer, Venue, Event
from events.models import TicketCategory
from orders.models import Promotion, Order
from tickets.models import Ticket

# cleanup any previous test data
User.objects.filter(username__in=['testcust','testorg']).delete()

# create organizer and venue and event
org_user = User.objects.create_user('testorg', 'org@example.com', 'pass')
organizer = Organizer.objects.create(user=org_user, organizer_name='Test Organizer')
venue = Venue.objects.create(venue_name='Test Venue', capacity=1000, address='Addr', city='City', has_reserved_seating=False)
event = Event.objects.create(event_datetime=timezone.now(), event_title='Test Event', venue=venue, organizer=organizer)

# create ticket category
category = TicketCategory.objects.create(category_name='General', quota=100, price=100.00, event=event)

# create promotion
promo = Promotion.objects.create(promo_code='TIKTAK20', discount_amount=10.00, quota=10, is_active=True)

# create customer and login
cust_user = User.objects.create_user('testcust', 'cust@example.com', 'pass')
customer = Customer.objects.create(user=cust_user, full_name='Test Cust', phone_number='081234')

c = Client()
logged = c.login(username='testcust', password='pass')
print('login:', logged)

# ensure testserver allowed for test client
settings.ALLOWED_HOSTS = ['testserver', 'localhost', '127.0.0.1']

# POST to create order
resp = c.post('/orders/create/', {'event': str(event.pk), 'category': str(category.pk), 'quantity': '3', 'promo_code': 'TIKTAK20'})
print('POST status code:', resp.status_code)

orders = Order.objects.filter(customer=customer)
print('orders count for customer:', orders.count())
if orders.exists():
    o = orders.latest('order_datetime')
    print('order total_price:', o.total_price, 'quantity:', o.quantity)
    tickets = Ticket.objects.filter(order=o)
    print('tickets created:', tickets.count())
    print('ticket codes:', [t.ticket_code for t in tickets])

# check OrderPromotion
from orders.models import OrderPromotion
ops = OrderPromotion.objects.filter(order__customer=customer)
print('orderpromotion count:', ops.count())

print('done')
