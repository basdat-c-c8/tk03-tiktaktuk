# ============================================================
# PATCH untuk seats/views.py (FULL REPLACEMENT)
# Trigger 5.1: Cek keterikatan Seat sebelum dihapus
# ============================================================

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
import uuid

from utils.db_connection import get_db_connection, extract_trigger_error
from accounts.views import get_user_role


@login_required
def seat_list(request):
    """Tampilkan daftar seat — raw SQL."""
    conn   = None
    cursor = None
    seats  = []

    try:
        conn   = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT s.seat_id, s.section, s.row_number, s.seat_number,
                   v.venue_name,
                   CASE WHEN hr.seat_id IS NOT NULL THEN TRUE ELSE FALSE END AS is_occupied
            FROM seat s
            LEFT JOIN venue v ON v.venue_id = s.venue_id
            LEFT JOIN has_relationship hr ON hr.seat_id = s.seat_id
            ORDER BY v.venue_name, s.section, s.row_number, s.seat_number
            """
        )
        rows = cursor.fetchall()
        seats = [
            {
                "seat_id":     r[0],
                "section":     r[1],
                "row_number":  r[2],
                "seat_number": r[3],
                "venue_name":  r[4],
                "is_occupied": r[5],
            }
            for r in rows
        ]
    except Exception as e:
        messages.error(request, f"Gagal memuat kursi: {e}")
    finally:
        if cursor: cursor.close()
        if conn:   conn.close()

    role = get_user_role(request.user)
    return render(request, 'seat.html', {'seats': seats, 'role': role})


@login_required
def seat_create(request):
    """Tambah seat baru — raw SQL."""
    role = get_user_role(request.user)
    if role not in ["admin", "penyelenggara"]:
        return redirect("main:show_main")

    if request.method == "POST":
        venue_id    = request.POST.get("venue_id", "").strip()
        section     = request.POST.get("section", "").strip()
        row_number  = request.POST.get("row_number", "").strip()
        seat_number = request.POST.get("seat_number", "").strip()

        conn   = None
        cursor = None

        try:
            conn   = get_db_connection()
            cursor = conn.cursor()

            new_seat_id = str(uuid.uuid4())
            cursor.execute(
                """
                INSERT INTO seat (seat_id, section, seat_number, row_number, venue_id)
                VALUES (%s, %s, %s, %s, %s)
                """,
                [new_seat_id, section, seat_number, row_number, venue_id]
            )
            conn.commit()
            messages.success(request, "Kursi berhasil ditambahkan.")

        except Exception as e:
            if conn: conn.rollback()
            error_msg = extract_trigger_error(e)
            messages.error(request, error_msg)

        finally:
            if cursor: cursor.close()
            if conn:   conn.close()

    return redirect("seats:seat_list")


@login_required
def seat_update(request, seat_id):
    """Update seat — raw SQL."""
    role = get_user_role(request.user)
    if role not in ["admin", "penyelenggara"]:
        return redirect("main:show_main")

    if request.method == "POST":
        section     = request.POST.get("section", "").strip()
        row_number  = request.POST.get("row_number", "").strip()
        seat_number = request.POST.get("seat_number", "").strip()

        conn   = None
        cursor = None

        try:
            conn   = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE seat
                SET section = %s, row_number = %s, seat_number = %s
                WHERE seat_id = %s
                """,
                [section, row_number, seat_number, str(seat_id)]
            )
            conn.commit()
            messages.success(request, "Kursi berhasil diperbarui.")

        except Exception as e:
            if conn: conn.rollback()
            error_msg = extract_trigger_error(e)
            messages.error(request, error_msg)

        finally:
            if cursor: cursor.close()
            if conn:   conn.close()

    return redirect("seats:seat_list")


@login_required
def seat_delete(request, seat_id):
    """
    Hapus seat — raw SQL.
    Trigger 5.1 aktif: jika seat sudah di-assign ke tiket,
    trigger akan RAISE EXCEPTION.
    """
    role = get_user_role(request.user)
    if role not in ["admin", "penyelenggara"]:
        return redirect("main:show_main")

    if request.method == "POST":
        conn   = None
        cursor = None

        try:
            conn   = get_db_connection()
            cursor = conn.cursor()

            # DELETE seat → memicu Trigger 5.1
            cursor.execute(
                "DELETE FROM seat WHERE seat_id = %s",
                [str(seat_id)]
            )
            conn.commit()
            messages.success(request, "Kursi berhasil dihapus.")

        except Exception as e:
            if conn: conn.rollback()

            # Pesan error dari Trigger 5.1 langsung tampil
            error_msg = extract_trigger_error(e)
            messages.error(request, error_msg)

        finally:
            if cursor: cursor.close()
            if conn:   conn.close()

    return redirect("seats:seat_list")


# ============================================================
# ============================================================
# PATCH untuk tickets/views.py (FULL REPLACEMENT)
# Trigger 5.2: Cek kuota Ticket Category saat membuat Ticket
# ============================================================
# ============================================================

# Simpan kode ini di tickets/views.py

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
import uuid

from utils.db_connection import get_db_connection, extract_trigger_error
from accounts.models import Customer
from accounts.views import get_user_role


@login_required
def ticket_list(request):
    """Tiket milik customer yang login — raw SQL."""
    conn    = None
    cursor  = None
    tickets = []

    try:
        conn   = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT customer_id FROM customer WHERE user_id = %s",
            [str(request.user.id)]
        )
        row = cursor.fetchone()

        if row:
            cust_id = row[0]
            cursor.execute(
                """
                SELECT t.ticket_id, t.ticket_code,
                       tc.category_name, e.event_title,
                       e.event_datetime, v.venue_name
                FROM ticket t
                JOIN ticket_category tc ON tc.category_id = t.tcategory_id
                JOIN event e ON e.event_id = tc.tevent_id
                LEFT JOIN venue v ON v.venue_id = e.venue_id
                JOIN "order" o ON o.order_id = t.torder_id
                WHERE o.customer_id = %s
                ORDER BY e.event_datetime DESC
                """,
                [str(cust_id)]
            )
            rows = cursor.fetchall()
            tickets = [
                {
                    "ticket_id":     r[0],
                    "ticket_code":   r[1],
                    "category_name": r[2],
                    "event_title":   r[3],
                    "event_datetime":r[4],
                    "venue_name":    r[5],
                }
                for r in rows
            ]
    except Exception as e:
        messages.error(request, f"Gagal memuat tiket: {e}")
    finally:
        if cursor: cursor.close()
        if conn:   conn.close()

    return render(request, 'ticket_customer.html', {'tickets': tickets})


@login_required
def ticket_admin_organizer(request):
    """
    Manajemen tiket untuk Admin/Organizer — raw SQL.
    Create Ticket → memicu Trigger 5.2 (cek kuota kategori).
    """
    role = get_user_role(request.user)

    conn    = None
    cursor  = None
    tickets = []

    try:
        conn   = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT t.ticket_id, t.ticket_code,
                   tc.category_name, e.event_title,
                   e.event_datetime, v.venue_name,
                   o.order_id, c.full_name
            FROM ticket t
            JOIN ticket_category tc ON tc.category_id = t.tcategory_id
            JOIN event e ON e.event_id = tc.tevent_id
            LEFT JOIN venue v ON v.venue_id = e.venue_id
            LEFT JOIN "order" o ON o.order_id = t.torder_id
            LEFT JOIN customer c ON c.customer_id = o.customer_id
            ORDER BY e.event_datetime DESC
            """
        )
        rows = cursor.fetchall()
        tickets = [
            {
                "ticket_id":      r[0],
                "ticket_code":    r[1],
                "category_name":  r[2],
                "event_title":    r[3],
                "event_datetime": r[4],
                "venue_name":     r[5],
                "order_id":       r[6],
                "customer_name":  r[7],
            }
            for r in rows
        ]
    except Exception as e:
        messages.error(request, f"Gagal memuat tiket: {e}")
    finally:
        if cursor: cursor.close()
        if conn:   conn.close()

    # Handle POST: Tambah Tiket Baru
    if request.method == "POST":
        order_id    = request.POST.get("order_id", "").strip()
        category_id = request.POST.get("category_id", "").strip()
        seat_id     = request.POST.get("seat_id", "").strip() or None

        conn2   = None
        cursor2 = None

        try:
            conn2   = get_db_connection()
            cursor2 = conn2.cursor()

            # Hitung jumlah tiket untuk generate kode
            cursor2.execute("SELECT COUNT(*) FROM ticket")
            existing_count = cursor2.fetchone()[0]
            idx  = existing_count + 1
            code = f"TKT-{idx:04d}"

            new_ticket_id = str(uuid.uuid4())

            # INSERT ticket → memicu Trigger 5.2 (cek kuota kategori)
            cursor2.execute(
                """
                INSERT INTO ticket (ticket_id, ticket_code, tcategory_id, torder_id)
                VALUES (%s, %s, %s, %s)
                """,
                [new_ticket_id, code, category_id, order_id]
            )

            # Jika seat dipilih, tambahkan relasi seat-ticket
            if seat_id:
                cursor2.execute(
                    """
                    INSERT INTO has_relationship (seat_id, ticket_id)
                    VALUES (%s, %s)
                    """,
                    [seat_id, new_ticket_id]
                )

            conn2.commit()
            messages.success(request, f'Tiket "{code}" berhasil dibuat.')

        except Exception as e:
            if conn2: conn2.rollback()

            # Pesan error dari Trigger 5.2 langsung tampil ke user
            error_msg = extract_trigger_error(e)
            messages.error(request, error_msg)

        finally:
            if cursor2: cursor2.close()
            if conn2:   conn2.close()

        return redirect('tickets:ticket_admin_organizer')

    return render(request, 'ticket_admin_organizer.html', {
        'tickets': tickets,
        'role':    role,
    })