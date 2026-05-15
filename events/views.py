from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_http_methods
from django.contrib import messages

from .models import Artist, TicketCategory
from .forms import ArtistForm, TicketCategoryForm
from accounts.models import Event
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


# ══════════════════════════════════════════════
#  ARTIST – CUD  (hanya Admin)
# ══════════════════════════════════════════════

@login_required
def artist_list(request):
    artists = Artist.objects.all().order_by('name')
    context = {
        'artists':       artists,
        'total_artists': artists.count(),
        'total_genres':  artists.exclude(genre__isnull=True).exclude(genre='').values('genre').distinct().count(),
        'total_event':   artists.count(),
           'role':          get_user_role(request.user),
    }
    return render(request, 'cudartist.html', context)


@login_required
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


@login_required
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


@login_required
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
    artists = Artist.objects.all().order_by('name')
    context = {
        'artists':       artists,
        'total_artists': artists.count(),
        'total_genres':  artists.exclude(genre__isnull=True).exclude(genre='').values('genre').distinct().count(),
           'role':          get_user_role(request.user),
    }
    return render(request, 'rartist.html', context)


# ══════════════════════════════════════════════
#  TICKET CATEGORY – CUD  (Admin & Organizer)
# ══════════════════════════════════════════════

@login_required
def ticket_category_manage(request):
    if not is_admin_or_organizer(request):
        messages.error(request, 'Akses ditolak.')
        return redirect('main:show_main')

    categories = TicketCategory.objects.select_related('event').all()

    # ambil event
    if get_user_role(request.user) == 'penyelenggara':
        events = Event.objects.filter(
            organizer=request.user
        ).order_by('event_title')

    else:
        events = Event.objects.all().order_by('event_title')

    form = TicketCategoryForm()

    # INI YANG PENTING
    form.fields['event'].queryset = events

    context = {
        'categories': categories,
        'events': events,
        'form': form,
        'role': get_user_role(request.user),
    }

    return render(request, 'cudticketcategory.html', context)


@login_required
@require_POST
def ticket_category_create(request):
    if not is_admin_or_organizer(request):
        return JsonResponse({'ok': False, 'error': 'Akses ditolak.'}, status=403)

    form = TicketCategoryForm(request.POST)
    if form.is_valid():
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


@login_required
def ticket_category_update(request, id):
    if not is_admin_or_organizer(request):
        return JsonResponse({'ok': False, 'error': 'Akses ditolak.'}, status=403)

    cat = get_object_or_404(TicketCategory, pk=id)

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
        form.save()
        return JsonResponse({'ok': True})
    return JsonResponse({'ok': False, 'errors': form.errors}, status=400)


@login_required
@require_POST
def ticket_category_delete(request, id):
    if not is_admin_or_organizer(request):
        return JsonResponse({'ok': False, 'error': 'Akses ditolak.'}, status=403)

    cat  = get_object_or_404(TicketCategory, pk=id)
    name = cat.category_name
    cat.delete()
    return JsonResponse({'ok': True, 'name': name})


# ══════════════════════════════════════════════
#  TICKET CATEGORY – READ  (semua pengguna)
# ══════════════════════════════════════════════

def ticket_category_read(request):
    categories = TicketCategory.objects.select_related('event').all()
    context = {
        'categories': categories,
        'events':     Event.objects.all().order_by('event_title'),
           'role':       get_user_role(request.user),
    }
    return render(request, 'rticketcategory.html', context)