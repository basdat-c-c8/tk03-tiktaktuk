import uuid
from accounts.models import Customer, Organizer, AccountRole, Seat
from events.models import TicketCategory
from accounts.models import Event
from orders.models import Order, Promotion, OrderPromotion
from tickets.models import Ticket

def get_user_role(user):
    """
    Consistency wrapper for get_user_role.
    Original implementation is in accounts/views.py.
    """
    try:
        from accounts.views import get_user_role as original_get_user_role
        return original_get_user_role(user)
    except ImportError:
        # Fallback if circular import occurs during migration
        if user.is_superuser:
            return 'admin'
        role_obj = AccountRole.objects.filter(user=user).first()
        return role_obj.role if role_obj else 'guest'

def get_current_customer(user):
    return Customer.objects.filter(user=user).first()

def get_current_organizer(user):
    return Organizer.objects.filter(user=user).first()

def filter_by_role(queryset, user, customer_field=None, organizer_field=None):
    """
    Generic role-based filter for querysets.
    """
    role = get_user_role(user)
    if user.is_superuser or role == 'admin':
        return queryset
    
    if role == 'penyelenggara' and organizer_field:
        organizer = get_current_organizer(user)
        if organizer:
            return queryset.filter(**{organizer_field: organizer})
        return queryset.none()
    
    if role == 'pelanggan' and customer_field:
        customer = get_current_customer(user)
        if customer:
            return queryset.filter(**{customer_field: customer})
        return queryset.none()
    
    return queryset.none()

def validate_event_ownership(user, event):
    """
    Checks if a user can manage a specific event.
    """
    role = get_user_role(user)
    if user.is_superuser or role == 'admin':
        return True
    if role == 'penyelenggara':
        organizer = get_current_organizer(user)
        return event.organizer == organizer
    return False

def get_available_seats(event):
    """
    Returns queryset of available seats for an event.
    """
    used_seat_ids = Ticket.objects.filter(
        order__event=event,
        seat__isnull=False
    ).values_list('seat_id', flat=True)
    
    return Seat.objects.filter(venue=event.venue).exclude(seat_id__in=used_seat_ids).order_by(
        'section', 'row_number', 'seat_number'
    )
