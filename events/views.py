# ============================================================
# PATCH untuk events/views.py (FULL REPLACEMENT)
# Trigger 3.1: Validasi duplikasi artist_id dan event_id pada EVENT_ARTIST
# SP 3.2: Stored Procedure sisa kuota Ticket Category
# ============================================================

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages
import uuid

from .models import Artist, TicketCategory
from .forms import ArtistForm, TicketCategoryForm
from accounts.models import Event
from accounts.views import get_user_role
from utils.db_connection import get_db_connection, extract_trigger_error


# ── Helpers ───────────────────────────────────────────────────────────────────

def is_admin(request):
    return get_user_role(request.user) == 'admin'

def is_admin_or_organizer(request):
    return get_user_role(request.user) in ('admin', 'penyelenggara')


# ══════════════════════════════════════════════════════════════════════════════
#  ARTIST — CRUD (tidak ada trigger di sini, tetap ORM boleh)
# ══════════════════════════════════════════════════════════════════════════════

@login_required
def artist_list(request):
    role    = get_user_role(request.user)
    artists = Artist.objects.all().order_by('name')

    context = {
        'artists':       artists,
        'total_artists': artists.count(),
        'total_genres':  artists.exclude(genre__isnull=True).exclude(genre='').values('genre').distinct().count(),
        'total_event':   artists.filter(eventartist__isnull=False).distinct().count(),
        'role':          role,
    }

    if role == 'admin':
        return render(request, 'cudartist.html', context)
    return render(request, 'rartist.html', context)


@login_required
@require_POST
def artist_create(request):
    if not is_admin(request):
        messages.error(request, 'Akses ditolak.')
        return redirect('events:artist_list')

    form = ArtistForm(request.POST)
    if form.is_valid():
        artist = form.save()
        messages.success(request, f'Artis "{artist.name}" berhasil ditambahkan.')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(request, error)

    return redirect('events:artist_list')


@login_required
@require_POST
def artist_update(request, id):
    if not is_admin(request):
        messages.error(request, 'Akses ditolak.')
        return redirect('events:artist_list')

    artist = get_object_or_404(Artist, pk=id)
    form   = ArtistForm(request.POST, instance=artist)

    if form.is_valid():
        form.save()
        messages.success(request, f'Artis "{artist.name}" berhasil diperbarui.')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(request, error)

    return redirect('events:artist_list')


@login_required
@require_POST
def artist_delete(request, id):
    if not is_admin(request):
        messages.error(request, 'Akses ditolak.')
        return redirect('events:artist_list')

    artist = get_object_or_404(Artist, pk=id)
    name   = artist.name
    artist.delete()
    messages.success(request, f'Artis "{name}" berhasil dihapus.')

    return redirect('events:artist_list')


@login_required
def artist_read(request):
    artists = Artist.objects.all().order_by('name')
    context = {
        'artists':       artists,
        'total_artists': artists.count(),
        'total_genres':  artists.exclude(genre__isnull=True).exclude(genre='').values('genre').distinct().count(),
        'total_event':   artists.filter(eventartist__isnull=False).distinct().count(),
        'role':          get_user_role(request.user),
    }
    return render(request, 'rartist.html', context)


# ══════════════════════════════════════════════════════════════════════════════
#  EVENT ARTIST — Trigger 3.1
#  Menambahkan Artist ke Event → trigger cek duplikasi + validasi keberadaan
# ══════════════════════════════════════════════════════════════════════════════

@login_required
def event_artist_list(request, event_id):
    """
    Tampilkan daftar artist yang terdaftar di suatu event,
    beserta sisa kuota tiket (Stored Procedure 3.2).
    """
    role   = get_user_role(request.user)
    conn   = None
    cursor = None
    artists_in_event = []
    ticket_quotas    = []
    event_title      = ""

    try:
        conn   = get_db_connection()
        cursor = conn.cursor()

        # Ambil judul event
        cursor.execute(
            "SELECT event_title FROM event WHERE event_id = %s",
            [str(event_id)]
        )
        row = cursor.fetchone()
        if row:
            event_title = row[0]

        # Ambil daftar artist di event ini
        cursor.execute(
            """
            SELECT ea.artist_id, a.name, a.genre, ea.role
            FROM event_artist ea
            JOIN artist a ON a.artist_id = ea.artist_id
            WHERE ea.event_id = %s
            ORDER BY a.name
            """,
            [str(event_id)]
        )
        rows = cursor.fetchall()
        artists_in_event = [
            {
                "artist_id": r[0],
                "name":      r[1],
                "genre":     r[2],
                "role":      r[3],
            }
            for r in rows
        ]

        # Panggil Stored Procedure 3.2: sisa kuota tiket per kategori
        cursor.execute(
            "SELECT * FROM sp_get_ticket_quota(%s)",
            [str(event_id)]
        )
        quota_rows = cursor.fetchall()
        ticket_quotas = [
            {
                "category_id":     r[0],
                "category_name":   r[1],
                "quota":           r[2],
                "tickets_sold":    r[3],
                "remaining_quota": r[4],
            }
            for r in quota_rows
        ]

    except Exception as e:
        error_msg = extract_trigger_error(e)
        messages.error(request, error_msg)

    finally:
        if cursor: cursor.close()
        if conn:   conn.close()

    # Semua artist yang tersedia (untuk dropdown tambah)
    all_artists = Artist.objects.all().order_by('name')

    context = {
        'event_id':          event_id,
        'event_title':       event_title,
        'artists_in_event':  artists_in_event,
        'ticket_quotas':     ticket_quotas,
        'all_artists':       all_artists,
        'role':              role,
    }

    return render(request, 'event_artist.html', context)


@login_required
def event_artist_add(request, event_id):
    """
    Tambahkan Artist ke Event — raw SQL.
    Trigger 3.1 aktif:
      - Cek artist_id ada
      - Cek event_id ada
      - Cek artist belum terdaftar di event yang sama
    Jika salah satu gagal → trigger RAISE EXCEPTION → pesan error tampil.
    """
    if not is_admin_or_organizer(request):
        messages.error(request, 'Akses ditolak.')
        return redirect('events:artist_list')

    if request.method == "POST":
        artist_id = request.POST.get("artist_id", "").strip()
        role_val  = request.POST.get("role", "Performer").strip()

        conn   = None
        cursor = None

        try:
            conn   = get_db_connection()
            cursor = conn.cursor()

            # INSERT ke event_artist → memicu Trigger 3.1
            # Trigger akan cek:
            #   1. artist_id ada di tabel artist
            #   2. event_id ada di tabel event
            #   3. kombinasi artist+event belum terdaftar
            cursor.execute(
                """
                INSERT INTO event_artist (event_id, artist_id, role)
                VALUES (%s, %s, %s)
                """,
                [str(event_id), artist_id, role_val]
            )

            conn.commit()
            messages.success(request, "Artist berhasil ditambahkan ke event.")

        except Exception as e:
            if conn: conn.rollback()

            # Pesan error dari Trigger 3.1 langsung ditampilkan
            error_msg = extract_trigger_error(e)
            messages.error(request, error_msg)

        finally:
            if cursor: cursor.close()
            if conn:   conn.close()

    return redirect('events:event_artist_list', event_id=event_id)


@login_required
def event_artist_remove(request, event_id, artist_id):
    """Hapus Artist dari Event — raw SQL."""
    if not is_admin_or_organizer(request):
        messages.error(request, 'Akses ditolak.')
        return redirect('events:artist_list')

    if request.method == "POST":
        conn   = None
        cursor = None

        try:
            conn   = get_db_connection()
            cursor = conn.cursor()

            cursor.execute(
                """
                DELETE FROM event_artist
                WHERE event_id = %s AND artist_id = %s
                """,
                [str(event_id), str(artist_id)]
            )
            conn.commit()
            messages.success(request, "Artist berhasil dihapus dari event.")

        except Exception as e:
            if conn: conn.rollback()
            error_msg = extract_trigger_error(e)
            messages.error(request, error_msg)

        finally:
            if cursor: cursor.close()
            if conn:   conn.close()

    return redirect('events:event_artist_list', event_id=event_id)


# ══════════════════════════════════════════════════════════════════════════════
#  TICKET CATEGORY — Tetap ORM (trigger ada di INSERT ticket, bukan category)
# ══════════════════════════════════════════════════════════════════════════════

@login_required
def ticket_category_manage(request):
    role       = get_user_role(request.user)
    categories = TicketCategory.objects.select_related('event').all()
    events     = Event.objects.all().order_by('event_title')

    all_cats    = TicketCategory.objects.all()
    total_quota = sum(c.quota for c in all_cats)
    max_price   = all_cats.order_by('-price').first()

    context = {
        'categories':       categories,
        'events':           events,
        'role':             role,
        'total_categories': all_cats.count(),
        'total_quota':      total_quota,
        'max_price':        max_price.price if max_price else 0,
    }

    if role in ('admin', 'penyelenggara'):
        return render(request, 'cudticketcategory.html', context)
    return render(request, 'rticketcategory.html', context)


@login_required
@require_POST
def ticket_category_create(request):
    if not is_admin_or_organizer(request):
        messages.error(request, 'Akses ditolak.')
        return redirect('events:ticket_category_manage')

    form = TicketCategoryForm(request.POST)
    if form.is_valid():
        cat = form.save()
        messages.success(request, f'Kategori "{cat.category_name}" berhasil ditambahkan.')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(request, error)

    return redirect('events:ticket_category_manage')


@login_required
@require_POST
def ticket_category_update(request, id):
    if not is_admin_or_organizer(request):
        messages.error(request, 'Akses ditolak.')
        return redirect('events:ticket_category_manage')

    cat  = get_object_or_404(TicketCategory, pk=id)
    form = TicketCategoryForm(request.POST, instance=cat)

    if form.is_valid():
        form.save()
        messages.success(request, f'Kategori "{cat.category_name}" berhasil diperbarui.')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(request, error)

    return redirect('events:ticket_category_manage')


@login_required
@require_POST
def ticket_category_delete(request, id):
    if not is_admin_or_organizer(request):
        messages.error(request, 'Akses ditolak.')
        return redirect('events:ticket_category_manage')

    cat  = get_object_or_404(TicketCategory, pk=id)
    name = cat.category_name
    cat.delete()
    messages.success(request, f'Kategori "{name}" berhasil dihapus.')

    return redirect('events:ticket_category_manage')


@login_required
def ticket_category_read(request):
    categories  = TicketCategory.objects.select_related('event').all()
    all_cats    = TicketCategory.objects.all()
    total_quota = sum(c.quota for c in all_cats)
    max_price   = all_cats.order_by('-price').first()

    context = {
        'categories':       categories,
        'events':           Event.objects.all().order_by('event_title'),
        'role':             get_user_role(request.user),
        'total_categories': all_cats.count(),
        'total_quota':      total_quota,
        'max_price':        max_price.price if max_price else 0,
    }
    return render(request, 'rticketcategory.html', context)


# ══════════════════════════════════════════════════════════════════════════════
#  STORED PROCEDURE 3.2 — Endpoint khusus untuk cek sisa kuota tiket
#  Bisa dipanggil via AJAX atau langsung dari halaman event detail
# ══════════════════════════════════════════════════════════════════════════════

@login_required
def ticket_quota_view(request, event_id):
    """
    Memanggil Stored Procedure sp_get_ticket_quota(event_id)
    dan menampilkan sisa kuota tiket per kategori untuk suatu event.
    """
    conn   = None
    cursor = None
    quotas = []
    event_title = ""

    try:
        conn   = get_db_connection()
        cursor = conn.cursor()

        # Ambil judul event
        cursor.execute(
            "SELECT event_title FROM event WHERE event_id = %s",
            [str(event_id)]
        )
        row = cursor.fetchone()
        if row:
            event_title = row[0]

        # Panggil stored procedure
        cursor.execute(
            "SELECT * FROM sp_get_ticket_quota(%s)",
            [str(event_id)]
        )
        rows = cursor.fetchall()
        quotas = [
            {
                "category_id":     r[0],
                "category_name":   r[1],
                "quota":           r[2],
                "tickets_sold":    r[3],
                "remaining_quota": r[4],
            }
            for r in rows
        ]

    except Exception as e:
        error_msg = extract_trigger_error(e)
        messages.error(request, error_msg)

    finally:
        if cursor: cursor.close()
        if conn:   conn.close()

    context = {
        'event_id':    event_id,
        'event_title': event_title,
        'quotas':      quotas,
        'role':        get_user_role(request.user),
    }

    return render(request, 'ticket_quota.html', context)