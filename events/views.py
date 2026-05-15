from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_http_methods
from django.contrib import messages
from django.db.models import Count, Q

from .models import Artist, EventArtist, TicketCategory
from .forms import ArtistForm, TicketCategoryForm
from accounts.models import Event, Organizer
from accounts.views import get_user_role


# ══════════════════════════════════════════════
#  HELPER – role checker (fixed to use DB lookup)
# ══════════════════════════════════════════════

def is_admin(request):
    """Check if current user is admin"""
    return get_user_role(request.user) == 'admin'


def is_admin_or_organizer(request):
    """Check if current user is admin or organizer"""
    role = get_user_role(request.user)
    return role in ('admin', 'penyelenggara')


def get_current_organizer(user):
    return Organizer.objects.filter(user=user).first()


def can_manage_ticket_category(request, category):
    role = get_user_role(request.user)
    if role == 'admin':
        return True

    if role != 'penyelenggara':
        return False

    organizer = get_current_organizer(request.user)
    return bool(organizer and category.event.organizer_id == organizer.organizer_id)


def get_artist_queryset(query=None):
    artists = Artist.objects.prefetch_related('eventartist_set__event').annotate(
        event_count=Count('eventartist', distinct=True)
    ).order_by('name')

    if query:
        artists = artists.filter(
            Q(name__icontains=query) |
            Q(genre__icontains=query) |
            Q(eventartist__event__event_title__icontains=query)
        ).distinct()

    return artists


def apply_artist_event_fallback(artists):
    artist_rows = list(artists)

    for artist in artist_rows:
        if artist.event_count == 0 and Event.objects.filter(event_title__icontains=artist.name).exists():
            artist.event_count = 1

    return artist_rows


# ══════════════════════════════════════════════
#  ARTIST – CUD  (hanya Admin)
# ══════════════════════════════════════════════
@login_required(login_url='/login')
def artist_list(request):
    if not is_admin(request):
        return redirect('events:artist_read')

    query = request.GET.get('q', '').strip()
    artists = get_artist_queryset(query)

    total_genres = (
        artists.exclude(genre__isnull=True)
        .exclude(genre='')
        .values('genre')
        .distinct()
        .count()
    )

    artist_rows = apply_artist_event_fallback(artists)
    total_event_artists = sum(1 for artist in artist_rows if artist.event_count > 0)

    context = {
        'artists': artist_rows,
        'total_artists': len(artist_rows),
        'total_genres': total_genres,
        'total_event': total_event_artists,
        'q': query,
        'role': get_user_role(request.user),
    }

    return render(request, 'cudartist.html', context)

    
@login_required(login_url='/login')
@require_POST
def artist_create(request):
    if not is_admin(request):
        return JsonResponse({'ok': False, 'error': 'Akses ditolak.'}, status=403)

    form = ArtistForm(request.POST)
    if form.is_valid():
        artist = form.save()
        return JsonResponse({
            'ok':    True,
            'id':    str(artist.artist_id),
            'name':  artist.name,
            'genre': artist.genre,
        })
    return JsonResponse({'ok': False, 'errors': form.errors}, status=400)


@login_required(login_url='/login')
def artist_update(request, id):
    if not is_admin(request):
        return JsonResponse({'ok': False, 'error': 'Akses ditolak.'}, status=403)

    artist = get_object_or_404(Artist, pk=id)

    if request.method == 'GET':
        return JsonResponse({
            'ok':    True,
            'id':    str(artist.artist_id),
            'name':  artist.name,
            'genre': artist.genre,
        })

    form = ArtistForm(request.POST, instance=artist)
    if form.is_valid():
        form.save()
        return JsonResponse({'ok': True, 'name': artist.name, 'genre': artist.genre})
    return JsonResponse({'ok': False, 'errors': form.errors}, status=400)


@login_required(login_url='/login')
@require_POST
def artist_delete(request, id):
    if not is_admin(request):
        return JsonResponse({'ok': False, 'error': 'Akses ditolak.'}, status=403)

    artist = get_object_or_404(Artist, pk=id)
    name   = artist.name
    artist.delete()
    return JsonResponse({'ok': True, 'name': name})


# ══════════════════════════════════════════════
#  ARTIST – READ  (semua pengguna)
# ══════════════════════════════════════════════

def artist_read(request):
    query = request.GET.get('q', '').strip()
    artists = get_artist_queryset(query)

    total_genres = artists.exclude(genre__isnull=True).exclude(genre='').values('genre').distinct().count()
    artist_rows = apply_artist_event_fallback(artists)
    total_event_artists = sum(1 for artist in artist_rows if artist.event_count > 0)
    
    role = get_user_role(request.user) if request.user.is_authenticated else 'guest'
    context = {
        'artists':       artist_rows,
        'total_artists': len(artist_rows),
        'total_genres':  total_genres,
        'total_event':   total_event_artists,
        'q':             query,
        'role':          role,
    }
    return render(request, 'rartist.html', context)


# ══════════════════════════════════════════════
#  TICKET CATEGORY – CUD  (Admin & Organizer)
# ══════════════════════════════════════════════

@login_required(login_url='/login')
def ticket_category_manage(request):
    if not is_admin_or_organizer(request):
        messages.error(request, 'Akses ditolak.')
        return redirect('main:show_main')

    role = get_user_role(request.user)
    organizer = get_current_organizer(request.user)

    categories = TicketCategory.objects.select_related('event', 'event__organizer').all()
    events = Event.objects.all().order_by('event_title')

    if role == 'penyelenggara':
        if organizer:
            categories = categories.filter(event__organizer=organizer)
            events = events.filter(organizer=organizer)
        else:
            categories = categories.none()
            events = events.none()

    form        = TicketCategoryForm()
    context = {
        'categories': categories,
        'events':     events,
        'form':       form,
           'role':       role,
    }
    return render(request, 'cudticketcategory.html', context)


@login_required(login_url='/login')
@require_POST
def ticket_category_create(request):
    if not is_admin_or_organizer(request):
        return JsonResponse({'ok': False, 'error': 'Akses ditolak.'}, status=403)

    form = TicketCategoryForm(request.POST)
    if form.is_valid():
        role = get_user_role(request.user)
        organizer = get_current_organizer(request.user)

        if role == 'penyelenggara':
            if not organizer:
                return JsonResponse({'ok': False, 'error': 'Organizer tidak ditemukan.'}, status=403)
            if form.cleaned_data['event'].organizer_id != organizer.organizer_id:
                return JsonResponse({'ok': False, 'error': 'Anda hanya dapat membuat kategori untuk event milik Anda.'}, status=403)

        cat = form.save()
        return JsonResponse({
            'ok':    True,
            'id':    str(cat.category_id),
            'name':  cat.category_name,
            'price': str(cat.price),
            'quota': cat.quota,
            'event': cat.event.event_title,
        })
    return JsonResponse({'ok': False, 'errors': form.errors}, status=400)


@login_required(login_url='/login')
def ticket_category_update(request, id):
    if not is_admin_or_organizer(request):
        return JsonResponse({'ok': False, 'error': 'Akses ditolak.'}, status=403)

    cat = get_object_or_404(TicketCategory, pk=id)

    if not can_manage_ticket_category(request, cat):
        return JsonResponse({'ok': False, 'error': 'Akses ditolak.'}, status=403)

    if request.method == 'GET':
        return JsonResponse({
            'ok':       True,
            'id':       str(cat.category_id),
            'name':     cat.category_name,
            'price':    str(cat.price),
            'quota':    cat.quota,
            'event_id': str(cat.event_id),
        })

    form = TicketCategoryForm(request.POST, instance=cat)
    if form.is_valid():
        role = get_user_role(request.user)
        organizer = get_current_organizer(request.user)

        if role == 'penyelenggara':
            if not organizer:
                return JsonResponse({'ok': False, 'error': 'Organizer tidak ditemukan.'}, status=403)
            if form.cleaned_data['event'].organizer_id != organizer.organizer_id:
                return JsonResponse({'ok': False, 'error': 'Anda hanya dapat memindahkan kategori ke event milik Anda.'}, status=403)

        form.save()
        return JsonResponse({'ok': True})
    return JsonResponse({'ok': False, 'errors': form.errors}, status=400)


@login_required(login_url='/login')
@require_POST
def ticket_category_delete(request, id):
    if not is_admin_or_organizer(request):
        return JsonResponse({'ok': False, 'error': 'Akses ditolak.'}, status=403)

    cat  = get_object_or_404(TicketCategory, pk=id)

    if not can_manage_ticket_category(request, cat):
        return JsonResponse({'ok': False, 'error': 'Akses ditolak.'}, status=403)

    name = cat.category_name
    cat.delete()
    return JsonResponse({'ok': True, 'name': name})


# ══════════════════════════════════════════════
#  TICKET CATEGORY – READ  (semua pengguna)
# ══════════════════════════════════════════════

def ticket_category_read(request):
    categories = TicketCategory.objects.select_related('event').all()
    role = get_user_role(request.user) if request.user.is_authenticated else 'guest'
    context = {
        'categories': categories,
        'events':     Event.objects.all().order_by('event_title'),
           'role':       role,
    }
    return render(request, 'rticketcategory.html', context)
