import uuid

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.shortcuts import redirect, render

from accounts.models import Customer, Seat
from accounts.views import get_current_organizer, get_user_role
from events.models import TicketCategory
from orders.models import Order
from .models import Ticket


def _is_admin(user, role=None):
    return user.is_superuser or (role or get_user_role(user)) == 'admin'


def _first_by_pk(queryset, value):
    if not value:
        return None
    try:
        return queryset.filter(pk=value).first()
    except (TypeError, ValueError, ValidationError):
        return None


def _visible_ticket_queryset(user):
    role = get_user_role(user)
    tickets = Ticket.objects.select_related(
        'order',
        'order__customer',
        'order__event',
        'order__event__organizer',
        'order__event__venue',
        'ticket_category',
        'ticket_category__event',
        'ticket_category__event__organizer',
        'ticket_category__event__venue',
        'seat',
    )

    if _is_admin(user, role):
        return tickets

    if role == 'penyelenggara':
        organizer = get_current_organizer(user)
        if organizer:
            return tickets.filter(order__event__organizer=organizer)
        return Ticket.objects.none()

    customer = Customer.objects.filter(user=user).first()
    if customer:
        return tickets.filter(order__customer=customer)
    return Ticket.objects.none()


def _management_querysets(user):
    role = get_user_role(user)
    orders = Order.objects.select_related('customer', 'event', 'event__organizer', 'event__venue')
    categories = TicketCategory.objects.select_related('event', 'event__organizer', 'event__venue')
    seats = Seat.objects.select_related('venue')

    if _is_admin(user, role):
        return orders, categories, seats

    if role == 'penyelenggara':
        organizer = get_current_organizer(user)
        if organizer:
            venue_ids = Order.objects.filter(event__organizer=organizer).values_list('event__venue_id', flat=True)
            return (
                orders.filter(event__organizer=organizer),
                categories.filter(event__organizer=organizer),
                seats.filter(venue_id__in=venue_ids),
            )

    return Order.objects.none(), TicketCategory.objects.none(), Seat.objects.none()


def _generate_ticket_code():
    for _ in range(20):
        candidate = f'TKT-{uuid.uuid4().hex[:8].upper()}'
        if not Ticket.objects.filter(ticket_code=candidate).exists():
            return candidate
    return f'TKT-{uuid.uuid4()}'


def _seat_assignment_error(seat, event, current_ticket=None):
    if seat is None:
        return ''

    if seat.venue_id != event.venue_id:
        return 'Kursi tidak sesuai dengan venue event.'

    existing = Ticket.objects.filter(order__event=event, seat=seat)
    if current_ticket:
        existing = existing.exclude(pk=current_ticket.pk)
    if existing.exists():
        return 'Kursi sudah terisi untuk event ini.'

    return ''


def _sync_order_quantity(order):
    ticket_count = order.tickets.count()
    if order.quantity != ticket_count:
        order.quantity = ticket_count
        order.save(update_fields=['quantity'])


@login_required
def ticket_list(request):
    role = get_user_role(request.user)
    if role != 'pelanggan':
        return redirect('tickets:ticket_admin_organizer')

    customer = Customer.objects.filter(user=request.user).first()
    tickets = (
        Ticket.objects.select_related('order', 'order__customer', 'ticket_category', 'ticket_category__event', 'ticket_category__event__venue', 'seat')
        .filter(order__customer=customer)
        if customer else Ticket.objects.none()
    )
    return render(request, 'ticket_customer.html', {
        'tickets': tickets,
        'ticket_count': tickets.count(),
        'role': role,
    })


@login_required
def ticket_admin_organizer(request):
    role = get_user_role(request.user)
    if not _is_admin(request.user, role) and role != 'penyelenggara':
        return redirect('tickets:ticket_list')

    visible_tickets = _visible_ticket_queryset(request.user)
    manageable_orders, manageable_categories, manageable_seats = _management_querysets(request.user)

    if request.method == 'POST':
        action = request.POST.get('action', '').strip()
        ticket_id = request.POST.get('ticket_id', '').strip()

        if action == 'create':
            order_id = request.POST.get('order_id', '').strip()
            category_id = request.POST.get('category_id', '').strip()
            seat_id = request.POST.get('seat_id', '').strip()

            order = _first_by_pk(manageable_orders, order_id)
            category = _first_by_pk(manageable_categories, category_id)
            seat = _first_by_pk(manageable_seats, seat_id)

            if not order or not category:
                messages.error(request, 'Order dan kategori tiket wajib dipilih.')
            elif category.event_id != order.event_id:
                messages.error(request, 'Kategori tiket harus sesuai dengan event pada order.')
            elif Ticket.objects.filter(ticket_category=category).count() >= category.quota:
                messages.error(request, 'Kuota kategori tiket sudah penuh.')
            elif seat_id and not seat:
                messages.error(request, 'Kursi yang dipilih tidak valid atau tidak dapat diakses.')
            else:
                seat_error = _seat_assignment_error(seat, order.event)
                if seat_error:
                    messages.error(request, seat_error)
                else:
                    ticket = Ticket.objects.create(
                        ticket_code=_generate_ticket_code(),
                        order=order,
                        ticket_category=category,
                        seat=seat,
                    )
                    _sync_order_quantity(order)
                    messages.success(request, f'Tiket {ticket.ticket_code} berhasil dibuat.')

        elif action == 'update':
            ticket = _first_by_pk(visible_tickets, ticket_id)
            category_id = request.POST.get('category_id', '').strip()
            seat_id = request.POST.get('seat_id', '').strip()

            if not ticket:
                messages.error(request, 'Tiket tidak ditemukan atau tidak dapat diakses.')
            else:
                category = ticket.ticket_category
                if category_id:
                    category = _first_by_pk(manageable_categories, category_id)

                seat = None
                if seat_id:
                    seat = _first_by_pk(manageable_seats, seat_id)

                if category_id and not category:
                    messages.error(request, 'Kategori tiket tidak valid.')
                elif category.event_id != ticket.order.event_id:
                    messages.error(request, 'Kategori tiket harus sesuai dengan event pada order.')
                elif category != ticket.ticket_category and Ticket.objects.filter(ticket_category=category).count() >= category.quota:
                    messages.error(request, 'Kuota kategori tiket sudah penuh.')
                elif seat_id and not seat:
                    messages.error(request, 'Kursi yang dipilih tidak valid atau tidak dapat diakses.')
                else:
                    seat_error = _seat_assignment_error(seat, ticket.order.event, current_ticket=ticket)
                    if seat_error:
                        messages.error(request, seat_error)
                    else:
                        ticket.ticket_category = category
                        ticket.seat = seat
                        ticket.save(update_fields=['ticket_category', 'seat'])
                        messages.success(request, f'Tiket {ticket.ticket_code} berhasil diperbarui.')

        elif action == 'delete':
            ticket = _first_by_pk(visible_tickets, ticket_id)
            if not ticket:
                messages.error(request, 'Tiket tidak ditemukan atau tidak dapat diakses.')
            else:
                order = ticket.order
                code = ticket.ticket_code
                ticket.delete()
                _sync_order_quantity(order)
                messages.success(request, f'Tiket {code} berhasil dihapus.')

        else:
            messages.error(request, 'Aksi tiket tidak dikenali.')

        return redirect('tickets:ticket_admin_organizer')

    visible_tickets = visible_tickets.order_by('-purchase_date')
    assigned_count = visible_tickets.exclude(seat__isnull=True).count()

    return render(request, 'ticket_admin_organizer.html', {
        'tickets': visible_tickets,
        'ticket_count': visible_tickets.count(),
        'assigned_count': assigned_count,
        'unassigned_count': visible_tickets.count() - assigned_count,
        'orders': manageable_orders.order_by('-order_datetime'),
        'categories': manageable_categories.order_by('event__event_title', 'category_name'),
        'seats': manageable_seats.order_by('venue__venue_name', 'section', 'row_number', 'seat_number'),
        'role': role,
    })
