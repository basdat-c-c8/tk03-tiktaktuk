# ============================================================
# PATCH untuk orders/views.py (FULL REPLACEMENT)
# Trigger 4: Validasi Promotion saat digunakan ke Order
# ============================================================

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
import uuid

from accounts.models import Event, Customer
from events.models import TicketCategory
from .models import Order, Promotion, OrderPromotion
from tickets.models import Ticket

from utils.db_connection import get_db_connection, extract_trigger_error


@login_required
def order_list(request):
    """Tampilkan daftar order — pakai raw SQL."""
    conn   = None
    cursor = None
    orders = []

    try:
        conn   = get_db_connection()
        cursor = conn.cursor()

        if request.user.is_superuser:
            cursor.execute(
                """
                SELECT o.order_id, o.order_date, o.payment_status,
                       o.total_amount, c.full_name
                FROM "order" o
                LEFT JOIN customer c ON c.customer_id = o.customer_id
                ORDER BY o.order_date DESC
                """
            )
        else:
            cursor.execute(
                "SELECT customer_id FROM customer WHERE user_id = %s",
                [str(request.user.id)]
            )
            row = cursor.fetchone()
            if row:
                cust_id = row[0]
                cursor.execute(
                    """
                    SELECT o.order_id, o.order_date, o.payment_status,
                           o.total_amount, c.full_name
                    FROM "order" o
                    LEFT JOIN customer c ON c.customer_id = o.customer_id
                    WHERE o.customer_id = %s
                    ORDER BY o.order_date DESC
                    """,
                    [str(cust_id)]
                )

        rows = cursor.fetchall()
        orders = [
            {
                "order_id":       r[0],
                "order_date":     r[1],
                "payment_status": r[2],
                "total_amount":   r[3],
                "customer_name":  r[4],
            }
            for r in rows
        ]

    except Exception as e:
        messages.error(request, f"Gagal memuat order: {e}")

    finally:
        if cursor: cursor.close()
        if conn:   conn.close()

    return render(request, 'orders/order_list.html', {'orders': orders})


@login_required
def order_create(request):
    """
    Buat order baru dengan raw SQL.
    Trigger 4 aktif saat INSERT ke order_promotion.
    """
    # Ambil data untuk form
    events     = Event.objects.all().order_by('-event_datetime')
    categories = TicketCategory.objects.select_related('event').all()

    if request.method == 'POST':
        event_id    = request.POST.get('event')
        category_id = request.POST.get('category')
        quantity    = int(request.POST.get('quantity') or 1)
        promo_code  = request.POST.get('promo_code', '').strip()

        conn   = None
        cursor = None

        try:
            conn   = get_db_connection()
            cursor = conn.cursor()

            # 1. Ambil customer_id dari user yang login
            cursor.execute(
                "SELECT customer_id FROM customer WHERE user_id = %s",
                [str(request.user.id)]
            )
            row = cursor.fetchone()
            if not row:
                messages.error(request, "Customer profile tidak ditemukan.")
                return redirect('main:profile')
            customer_id = row[0]

            # 2. Ambil harga dari ticket_category
            cursor.execute(
                "SELECT price FROM ticket_category WHERE category_id = %s",
                [category_id]
            )
            row = cursor.fetchone()
            if not row:
                messages.error(request, "Kategori tiket tidak ditemukan.")
                return redirect('orders:order_create')
            price = float(row[0])
            total = price * quantity

            # 3. Buat order baru
            new_order_id = str(uuid.uuid4())
            cursor.execute(
                """
                INSERT INTO "order" (order_id, order_date, payment_status, total_amount, customer_id)
                VALUES (%s, NOW(), 'Pending', %s, %s)
                """,
                [new_order_id, total, str(customer_id)]
            )

            # 4. Buat tiket sejumlah quantity
            cursor.execute("SELECT COUNT(*) FROM ticket")
            existing_count = cursor.fetchone()[0]

            for i in range(quantity):
                idx       = existing_count + i + 1
                code      = f"TKT-{idx:04d}"
                ticket_id = str(uuid.uuid4())

                # INSERT ticket → memicu Trigger 5.2 (cek kuota)
                cursor.execute(
                    """
                    INSERT INTO ticket (ticket_id, ticket_code, tcategory_id, torder_id)
                    VALUES (%s, %s, %s, %s)
                    """,
                    [ticket_id, code, category_id, new_order_id]
                )

            # 5. Terapkan promo jika ada
            if promo_code:
                # Cari promotion_id dari promo_code
                cursor.execute(
                    "SELECT promotion_id FROM promotion WHERE promo_code ILIKE %s",
                    [promo_code]
                )
                promo_row = cursor.fetchone()

                if not promo_row:
                    # Pesan tidak ditemukan — rollback dan tampilkan error
                    conn.rollback()
                    messages.error(
                        request,
                        f'ERROR: Kode promo "{promo_code}" tidak ditemukan.'
                    )
                    return render(request, 'orders/order_create.html', {
                        'events': events,
                        'categories': categories,
                    })

                promotion_id      = promo_row[0]
                order_promo_id    = str(uuid.uuid4())

                # INSERT ke order_promotion → memicu Trigger 4
                # (cek usage_limit + validasi tanggal event)
                cursor.execute(
                    """
                    INSERT INTO order_promotion (order_promotion_id, promotion_id, order_id)
                    VALUES (%s, %s, %s)
                    """,
                    [order_promo_id, str(promotion_id), new_order_id]
                )

            conn.commit()
            messages.success(request, f'Order berhasil dibuat dengan {quantity} tiket.')
            return redirect('orders:order_list')

        except Exception as e:
            if conn:
                conn.rollback()

            # Pesan error dari trigger langsung ditampilkan ke user
            error_msg = extract_trigger_error(e)
            messages.error(request, error_msg)

        finally:
            if cursor: cursor.close()
            if conn:   conn.close()

    return render(request, 'orders/order_create.html', {
        'events':     events,
        'categories': categories,
    })


def promotion_list(request):
    """Tampilkan daftar promosi — raw SQL."""
    conn   = None
    cursor = None
    promos = []

    try:
        conn   = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT promotion_id, promo_code, discount_type,
                   discount_value, start_date, end_date, usage_limit,
                   (SELECT COUNT(*) FROM order_promotion
                    WHERE promotion_id = p.promotion_id) AS usage_count
            FROM promotion p
            ORDER BY promo_code
            """
        )
        rows = cursor.fetchall()
        promos = [
            {
                "promotion_id":   r[0],
                "promo_code":     r[1],
                "discount_type":  r[2],
                "discount_value": r[3],
                "start_date":     r[4],
                "end_date":       r[5],
                "usage_limit":    r[6],
                "usage_count":    r[7],
            }
            for r in rows
        ]
    except Exception as e:
        messages.error(request, f"Gagal memuat promosi: {e}")
    finally:
        if cursor: cursor.close()
        if conn:   conn.close()

    return render(request, 'orders/promotion_list.html', {'promos': promos})