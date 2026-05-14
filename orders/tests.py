from decimal import Decimal

from django.contrib.auth.models import User
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.models import AccountRole, Customer, Event, Organizer, Role, Seat, Venue
from events.models import TicketCategory
from tickets.models import Ticket
from .models import Order, Promotion


@override_settings(ALLOWED_HOSTS=['testserver', 'localhost', '127.0.0.1'])
class TK03ComplianceSmokeTests(TestCase):
    def setUp(self):
        self.admin_role = Role.objects.create(role_name='admin')
        self.organizer_role = Role.objects.create(role_name='penyelenggara')
        self.customer_role = Role.objects.create(role_name='pelanggan')

        self.admin_user = User.objects.create_user('adminuser', password='pass')
        AccountRole.objects.create(user=self.admin_user, role=self.admin_role)

        self.org_user = User.objects.create_user('orgone', password='pass')
        self.other_org_user = User.objects.create_user('orgtwo', password='pass')
        AccountRole.objects.create(user=self.org_user, role=self.organizer_role)
        AccountRole.objects.create(user=self.other_org_user, role=self.organizer_role)
        self.organizer = Organizer.objects.create(user=self.org_user, organizer_name='Org One')
        self.other_organizer = Organizer.objects.create(user=self.other_org_user, organizer_name='Org Two')

        self.customer_user = User.objects.create_user('custone', password='pass')
        self.other_customer_user = User.objects.create_user('custtwo', password='pass')
        AccountRole.objects.create(user=self.customer_user, role=self.customer_role)
        AccountRole.objects.create(user=self.other_customer_user, role=self.customer_role)
        self.customer = Customer.objects.create(user=self.customer_user, full_name='Cust One')
        self.other_customer = Customer.objects.create(user=self.other_customer_user, full_name='Cust Two')

        self.venue = Venue.objects.create(
            venue_name='Reserved Hall',
            capacity=100,
            address='Addr',
            city='Jakarta',
            has_reserved_seating=True,
        )
        self.other_venue = Venue.objects.create(
            venue_name='Other Hall',
            capacity=100,
            address='Addr',
            city='Bandung',
            has_reserved_seating=True,
        )
        self.event = Event.objects.create(
            event_datetime=timezone.now(),
            event_title='Org One Event',
            venue=self.venue,
            organizer=self.organizer,
        )
        self.other_event = Event.objects.create(
            event_datetime=timezone.now(),
            event_title='Org Two Event',
            venue=self.other_venue,
            organizer=self.other_organizer,
        )
        self.category = TicketCategory.objects.create(
            category_name='VIP',
            quota=10,
            price=Decimal('100000.00'),
            event=self.event,
        )
        self.other_category = TicketCategory.objects.create(
            category_name='REG',
            quota=10,
            price=Decimal('50000.00'),
            event=self.other_event,
        )
        self.seat_a1 = Seat.objects.create(venue=self.venue, section='A', row_number='1', seat_number='1')
        self.seat_a2 = Seat.objects.create(venue=self.venue, section='A', row_number='1', seat_number='2')
        self.seat_b1 = Seat.objects.create(venue=self.other_venue, section='B', row_number='1', seat_number='1')

        self.order = Order.objects.create(
            customer=self.customer,
            event=self.event,
            total_price=Decimal('100000.00'),
            quantity=1,
        )
        self.other_order = Order.objects.create(
            customer=self.other_customer,
            event=self.other_event,
            total_price=Decimal('50000.00'),
            quantity=1,
        )
        self.ticket = Ticket.objects.create(
            ticket_code='TKT-OWN',
            order=self.order,
            ticket_category=self.category,
            seat=self.seat_a1,
        )
        self.other_ticket = Ticket.objects.create(
            ticket_code='TKT-OTHER',
            order=self.other_order,
            ticket_category=self.other_category,
            seat=self.seat_b1,
        )
        self.promo = Promotion.objects.create(
            promo_code='SAVE10',
            discount_amount=Decimal('10000.00'),
            quota=5,
            is_active=True,
        )
        self.client = Client()

    def test_ticket_read_scope_by_role(self):
        self.client.login(username='adminuser', password='pass')
        response = self.client.get(reverse('tickets:ticket_admin_organizer'))
        self.assertContains(response, 'TKT-OWN')
        self.assertContains(response, 'TKT-OTHER')

        self.client.login(username='orgone', password='pass')
        response = self.client.get(reverse('tickets:ticket_admin_organizer'))
        self.assertContains(response, 'TKT-OWN')
        self.assertNotContains(response, 'TKT-OTHER')

        self.client.login(username='custone', password='pass')
        response = self.client.get(reverse('tickets:ticket_list'))
        self.assertContains(response, 'TKT-OWN')
        self.assertNotContains(response, 'TKT-OTHER')

    def test_ticket_crud_and_organizer_ownership_guard(self):
        self.client.login(username='orgtwo', password='pass')
        self.client.post(reverse('tickets:ticket_admin_organizer'), {
            'action': 'update',
            'ticket_id': self.ticket.pk,
            'category_id': self.category.pk,
            'seat_id': self.seat_a2.pk,
        })
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.seat_id, self.seat_a1.pk)

        self.client.login(username='orgone', password='pass')
        self.client.post(reverse('tickets:ticket_admin_organizer'), {
            'action': 'update',
            'ticket_id': self.ticket.pk,
            'category_id': self.category.pk,
            'seat_id': self.seat_a2.pk,
        })
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.seat_id, self.seat_a2.pk)

        self.client.login(username='adminuser', password='pass')
        create_response = self.client.post(reverse('tickets:ticket_admin_organizer'), {
            'action': 'create',
            'order_id': self.order.pk,
            'category_id': self.category.pk,
            'seat_id': '',
        })
        self.assertEqual(create_response.status_code, 302)
        self.assertEqual(Ticket.objects.filter(order=self.order).count(), 2)

        created_ticket = Ticket.objects.filter(order=self.order, seat__isnull=True).first()
        delete_response = self.client.post(reverse('tickets:ticket_admin_organizer'), {
            'action': 'delete',
            'ticket_id': created_ticket.pk,
        })
        self.assertEqual(delete_response.status_code, 302)
        self.assertFalse(Ticket.objects.filter(pk=created_ticket.pk).exists())

    def test_seat_create_update_and_role_guard(self):
        self.client.login(username='custone', password='pass')
        response = self.client.get(reverse('seats:seat_list'))
        self.assertEqual(response.status_code, 302)

        self.client.login(username='orgone', password='pass')
        response = self.client.get(reverse('seats:seat_list'))
        self.assertContains(response, 'Reserved Hall')
        self.assertNotContains(response, 'Other Hall')

        self.client.post(reverse('seats:seat_list'), {
            'action': 'create',
            'venue_id': self.venue.pk,
            'section': 'A',
            'row_number': '1',
            'seat_number': '3',
        })
        self.assertTrue(Seat.objects.filter(venue=self.venue, section='A', row_number='1', seat_number='3').exists())

        self.client.post(reverse('seats:seat_list'), {
            'action': 'create',
            'venue_id': self.other_venue.pk,
            'section': 'X',
            'row_number': '1',
            'seat_number': '1',
        })
        self.assertFalse(Seat.objects.filter(venue=self.other_venue, section='X').exists())

        self.client.post(reverse('seats:seat_list'), {
            'action': 'update',
            'seat_id': self.seat_a1.pk,
            'venue_id': self.other_venue.pk,
            'section': 'Moved',
            'row_number': '1',
            'seat_number': '9',
        })
        self.seat_a1.refresh_from_db()
        self.assertEqual(self.seat_a1.venue_id, self.venue.pk)

    def test_checkout_assigns_real_seat_and_blocks_duplicate(self):
        self.client.login(username='custone', password='pass')
        response = self.client.post(reverse('orders:order_create'), {
            'event': self.event.pk,
            'category': self.category.pk,
            'quantity': '1',
            'promo_code': 'SAVE10',
            'seat_ids': [str(self.seat_a2.pk)],
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Ticket.objects.filter(order__event=self.event, seat=self.seat_a2).count(), 1)

        self.client.login(username='custtwo', password='pass')
        duplicate_response = self.client.post(reverse('orders:order_create'), {
            'event': self.event.pk,
            'category': self.category.pk,
            'quantity': '1',
            'seat_ids': [str(self.seat_a2.pk)],
        })
        self.assertEqual(duplicate_response.status_code, 200)
        self.assertEqual(Ticket.objects.filter(order__event=self.event, seat=self.seat_a2).count(), 1)

        invalid_response = self.client.post(reverse('orders:order_create'), {
            'event': self.event.pk,
            'category': self.category.pk,
            'quantity': '1',
            'seat_ids': [str(self.seat_b1.pk)],
        })
        self.assertEqual(invalid_response.status_code, 200)
        self.assertEqual(Ticket.objects.filter(order__event=self.event, seat=self.seat_b1).count(), 0)

    def test_guest_is_redirected_from_management_pages(self):
        self.client.logout()
        self.assertEqual(self.client.get(reverse('main:login')).status_code, 200)
        self.assertEqual(self.client.get(reverse('main:register')).status_code, 200)
        self.assertEqual(self.client.get(reverse('seats:seat_list')).status_code, 302)
        self.assertEqual(self.client.get(reverse('tickets:ticket_list')).status_code, 302)
        self.assertEqual(self.client.get(reverse('orders:order_list')).status_code, 302)
