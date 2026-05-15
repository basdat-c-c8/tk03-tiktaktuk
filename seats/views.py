from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.shortcuts import redirect, render

from accounts.models import Event, Seat, Venue
from accounts.views import get_current_organizer, get_user_role
from tickets.models import Ticket
from utils.db_connection import get_db_connection, extract_trigger_error

def _is_admin(user, role=None):
    return user.is_superuser or (role or get_user_role(user)) == 'admin'


def _first_by_pk(queryset, value):
    if not value:
        return None
    try:
        return queryset.filter(pk=value).first()
    except (TypeError, ValueError, ValidationError):
        return None


def _manageable_venues(user):
    role = get_user_role(user)
    if _is_admin(user, role):
        return Venue.objects.all().order_by('venue_name')

    if role == 'penyelenggara':
        organizer = get_current_organizer(user)
        if not organizer:
            return Venue.objects.none()

        own_venue_ids = Event.objects.filter(organizer=organizer).values_list('venue_id', flat=True).distinct()
        other_venue_ids = Event.objects.exclude(organizer=organizer).values_list('venue_id', flat=True).distinct()
        return Venue.objects.filter(venue_id__in=own_venue_ids).exclude(venue_id__in=other_venue_ids).order_by('venue_name')

    return Venue.objects.none()


def _seat_is_occupied(seat):
    return Ticket.objects.filter(seat=seat).exists()


def _clean_seat_value(value):
    return (value or '').strip()


@login_required(login_url='/login')
def seat_list(request):
    role = get_user_role(request.user)
    if not _is_admin(request.user, role) and role != 'penyelenggara':
        return redirect('main:show_main')

    manageable_venues = _manageable_venues(request.user)

    if request.method == 'POST':
        action = request.POST.get('action', '').strip()
        venue_id = request.POST.get('venue_id', '').strip()
        section = _clean_seat_value(request.POST.get('section'))
        row_number = _clean_seat_value(request.POST.get('row_number'))
        seat_number = _clean_seat_value(request.POST.get('seat_number'))
        venue = _first_by_pk(manageable_venues, venue_id)

        if action == 'delete':
            seat_id = request.POST.get('seat_id', '').strip()
            seat = _first_by_pk(
                Seat.objects.filter(venue__in=manageable_venues),
                seat_id
            )
            if not seat:
                messages.error(request, 'Kursi tidak ditemukan atau tidak dapat diakses.')
            else:
                try:
                    seat.delete()
                    messages.success(request, 'Kursi berhasil dihapus.')
                except Exception as e:
                    # Error dari trigger 5.1: kursi sudah terisi
                    messages.error(request, extract_trigger_error(e))
            return redirect('seats:seat_list')
 
        if action not in ('create', 'update'):
            messages.error(request, 'Aksi kursi tidak dikenali.')
            return redirect('seats:seat_list')

        if not venue:
            messages.error(request, 'Venue tidak valid atau tidak dapat diakses.')
            return redirect('seats:seat_list')

        if not section or not row_number or not seat_number:
            messages.error(request, 'Section, baris, dan nomor kursi wajib diisi.')
            return redirect('seats:seat_list')

        seat = None
        if action == 'update':
            seat_id = request.POST.get('seat_id', '').strip()
            seat = _first_by_pk(Seat.objects.filter(venue__in=manageable_venues), seat_id)
            if not seat:
                messages.error(request, 'Kursi tidak ditemukan atau tidak dapat diakses.')
                return redirect('seats:seat_list')
            if _seat_is_occupied(seat) and venue.pk != seat.venue_id:
                messages.error(request, 'Kursi yang sudah terisi tidak boleh dipindah ke venue lain.')
                return redirect('seats:seat_list')

        duplicate = Seat.objects.filter(
            venue=venue,
            section__iexact=section,
            row_number__iexact=row_number,
            seat_number__iexact=seat_number,
        )
        if seat:
            duplicate = duplicate.exclude(pk=seat.pk)
        if duplicate.exists():
            messages.error(request, 'Kursi dengan section, baris, dan nomor tersebut sudah ada di venue ini.')
            return redirect('seats:seat_list')

        if action == 'create':
            Seat.objects.create(
                venue=venue,
                section=section,
                row_number=row_number,
                seat_number=seat_number,
            )
            messages.success(request, 'Kursi berhasil ditambahkan.')
        else:
            seat.venue = venue
            seat.section = section
            seat.row_number = row_number
            seat.seat_number = seat_number
            seat.save(update_fields=['venue', 'section', 'row_number', 'seat_number'])
            messages.success(request, 'Kursi berhasil diperbarui.')

        return redirect('seats:seat_list')

    seats = Seat.objects.select_related('venue').filter(venue__in=manageable_venues).order_by('venue__venue_name', 'section', 'row_number', 'seat_number')

    used_seat_ids = set(
        Ticket.objects.exclude(seat__isnull=True).values_list('seat_id', flat=True)
    )
    total_seats = seats.count()
    filled_count = sum(1 for seat in seats if seat.seat_id in used_seat_ids)

    return render(request, 'seat.html', {
        'role': role,
        'seats': seats,
        'venues': manageable_venues,
        'used_seat_ids': used_seat_ids,
        'total_seats': total_seats,
        'available_count': total_seats - filled_count,
        'filled_count': filled_count,
        'delete_supported': True,
    })
