from decimal import Decimal, InvalidOperation
import uuid

from django.db import transaction
from django.db.models import Q, Sum
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from accounts.models import Event, Customer, Seat
from accounts.views import get_user_role, get_current_organizer
from events.models import TicketCategory
from .models import Order, Promotion, OrderPromotion
from tickets.models import Ticket


def _get_customer(user):
	return Customer.objects.filter(user=user).first()


def _first_by_pk(queryset, value):
	if not value:
		return None
	try:
		return queryset.filter(pk=value).first()
	except (TypeError, ValueError, ValidationError):
		return None


def _valid_uuid_values(values):
	for value in values:
		try:
			uuid.UUID(str(value))
		except (TypeError, ValueError):
			return False
	return True


def _parse_positive_int(value, default=None):
	try:
		parsed = int(value)
	except (TypeError, ValueError):
		return default
	return parsed if parsed > 0 else default


def _parse_date_value(value):
	if not value:
		return None
	return parse_date(value.strip())


def _get_active_promos():
	today = timezone.localdate()
	return Promotion.objects.filter(is_active=True).filter(
		Q(start_date__isnull=True) | Q(start_date__lte=today),
		Q(end_date__isnull=True) | Q(end_date__gte=today),
	).order_by('promo_code')


def _generate_ticket_code():
	for _ in range(20):
		candidate = f'TKT-{uuid.uuid4().hex[:8].upper()}'
		if not Ticket.objects.filter(ticket_code=candidate).exists():
			return candidate
	return f'TKT-{uuid.uuid4()}'


def _available_seats_for_event(event):
	if not event:
		return Seat.objects.none()

	used_seat_ids = Ticket.objects.filter(
		order__event=event,
		seat__isnull=False,
	).values_list('seat_id', flat=True)
	return Seat.objects.filter(venue=event.venue).exclude(seat_id__in=used_seat_ids).order_by(
		'section',
		'row_number',
		'seat_number',
	)


def _get_order_queryset_for_user(user):
	role = get_user_role(user)
	queryset = Order.objects.select_related('customer', 'event', 'event__organizer', 'event__venue').order_by('-order_datetime')

	if user.is_superuser or role == 'admin':
		return queryset

	if role == 'penyelenggara':
		organizer = get_current_organizer(user)
		if organizer:
			return queryset.filter(event__organizer=organizer)
		return Order.objects.none()

	customer = _get_customer(user)
	if customer:
		return queryset.filter(customer=customer)
	return Order.objects.none()


@login_required
def order_list(request):
	role = get_user_role(request.user)
	if request.method == 'POST':
		if role != 'admin' and not request.user.is_superuser:
			messages.error(request, 'Hanya admin yang dapat mengubah order.')
			return redirect('orders:order_list')

		action = request.POST.get('action', '').strip()
		order_id = request.POST.get('order_id', '').strip()
		order = get_object_or_404(Order, pk=order_id)

		if action == 'update':
			payment_status = request.POST.get('payment_status', '').strip().lower()
			allowed_statuses = {'pending', 'lunas', 'paid', 'dibatalkan', 'cancelled'}
			if payment_status not in allowed_statuses:
				messages.error(request, 'Status pembayaran tidak valid.')
				return redirect('orders:order_list')

			order.payment_status = 'cancelled' if payment_status == 'dibatalkan' else payment_status
			order.save(update_fields=['payment_status'])
			messages.success(request, 'Status order berhasil diperbarui.')
		elif action == 'delete':
			order.delete()
			messages.success(request, 'Order berhasil dihapus.')
		else:
			messages.error(request, 'Aksi order tidak dikenali.')

		return redirect('orders:order_list')

	orders = _get_order_queryset_for_user(request.user)
	paid_orders = orders.filter(payment_status__in=['lunas', 'paid'])
	total_revenue = paid_orders.aggregate(total=Sum('total_price'))['total'] or Decimal('0')
	return render(request, 'orders/order_list.html', {
		'orders': orders,
		'role': role,
		'order_count': orders.count(),
		'paid_count': paid_orders.count(),
		'pending_count': orders.filter(payment_status='pending').count(),
		'total_revenue': total_revenue,
	})


@login_required
def order_create(request):
	if get_user_role(request.user) != 'pelanggan':
		messages.error(request, 'Halaman checkout hanya untuk pelanggan.')
		return redirect('main:show_main')

	selected_event_id = request.GET.get('event_id', '').strip()
	selected_category_id = request.GET.get('category_id', '').strip()
	selected_quantity = _parse_positive_int(request.GET.get('quantity'), default=1) or 1
	promo_code = request.GET.get('promo_code', '').strip()

	events = Event.objects.select_related('venue', 'organizer').all().order_by('-event_datetime')
	categories = TicketCategory.objects.select_related('event', 'event__venue').all().order_by('category_name')
	selected_event = None
	selected_category = None
	active_promos = _get_active_promos()
	selected_seat_ids = []

	if selected_event_id:
		selected_event = _first_by_pk(events, selected_event_id)
		if selected_event:
			categories = categories.filter(event=selected_event)
		else:
			selected_event_id = ''

	if not selected_event:
		selected_event = events.first()
		if selected_event:
			selected_event_id = str(selected_event.pk)
			categories = categories.filter(event=selected_event)

	if selected_category_id:
		selected_category = _first_by_pk(categories, selected_category_id)

	if not selected_category:
		selected_category = categories.first()
		if selected_category:
			selected_category_id = str(selected_category.pk)

	checkout_error = ''

	if request.method == 'POST':
		event_id = request.POST.get('event', '').strip()
		category_id = request.POST.get('category', '').strip()
		quantity = _parse_positive_int(request.POST.get('quantity'), default=1)
		promo_code = request.POST.get('promo_code', '').strip()
		selected_seat_ids = [seat_id.strip() for seat_id in request.POST.getlist('seat_ids') if seat_id.strip()]
		selected_quantity = quantity or 1
		selected_event_id = event_id or selected_event_id
		selected_category_id = category_id or selected_category_id

		customer = _get_customer(request.user)
		if not customer:
			messages.error(request, 'Profil customer tidak ditemukan.')
			return redirect('main:profile')

		if not event_id or not category_id:
			checkout_error = 'Event dan kategori tiket harus dipilih.'
		else:
			event = _first_by_pk(Event.objects.select_related('venue', 'organizer'), event_id)
			category = _first_by_pk(TicketCategory.objects.select_related('event', 'event__venue'), category_id)
			selected_event = event
			selected_category = category
			if selected_event:
				categories = TicketCategory.objects.select_related('event', 'event__venue').filter(event=selected_event).order_by('category_name')

			if not event or not category:
				checkout_error = 'Event atau kategori tiket tidak valid.'
			elif category.event_id != event.event_id:
				checkout_error = 'Kategori tiket tidak cocok dengan event yang dipilih.'
			elif quantity is None or quantity < 1 or quantity > 10:
				checkout_error = 'Jumlah tiket harus antara 1 dan 10.'
			else:
				sold_count = Ticket.objects.filter(ticket_category=category).count()
				available_quota = max(category.quota - sold_count, 0)
				if quantity > available_quota:
					checkout_error = f'Kuota tiket tersisa hanya {available_quota}.'
				else:
					selected_seats = []
					if event.venue.has_reserved_seating:
						if len(selected_seat_ids) != quantity:
							checkout_error = 'Jumlah kursi yang dipilih harus sama dengan jumlah tiket.'
						elif len(set(selected_seat_ids)) != len(selected_seat_ids):
							checkout_error = 'Pilihan kursi tidak boleh duplikat.'
						elif not _valid_uuid_values(selected_seat_ids):
							checkout_error = 'Kursi yang dipilih tidak valid.'
						else:
							seat_queryset = Seat.objects.filter(seat_id__in=selected_seat_ids, venue=event.venue)
							seat_by_id = {str(seat.seat_id): seat for seat in seat_queryset}
							if len(seat_by_id) != quantity:
								checkout_error = 'Kursi yang dipilih tidak valid untuk venue event ini.'
							elif Ticket.objects.filter(order__event=event, seat_id__in=selected_seat_ids).exists():
								checkout_error = 'Salah satu kursi sudah terisi untuk event ini.'
							else:
								selected_seats = [seat_by_id[seat_id] for seat_id in selected_seat_ids]

					line_total = Decimal(category.price) * Decimal(quantity)
					discount_amount = Decimal('0')
					promo = None

					if promo_code and not checkout_error:
						promo = Promotion.objects.filter(promo_code__iexact=promo_code, is_active=True).first()
						if not promo:
							checkout_error = 'Kode promo tidak valid atau sudah nonaktif.'
						elif not promo.is_currently_active():
							checkout_error = 'Kode promo belum aktif atau sudah berakhir.'
						else:
							used_quota = OrderPromotion.objects.filter(promotion=promo).count()
							if promo.quota > 0 and used_quota >= promo.quota:
								checkout_error = 'Kuota promo sudah habis.'
								promo = None
							else:
								discount_amount = promo.calculate_discount(line_total)

					if not checkout_error:
						total = max(line_total - discount_amount, Decimal('0'))

						# TODO(TK04): Transaction-sensitive flow.
						# TRANSACTION_CANDIDATE: This block must be atomic.
						# TRIGGER_CANDIDATE: Seat occupancy and promo quota validation.
						# STORED_PROCEDURE_CANDIDATE: create_order(customer_id, event_id, category_id, seats, promo_code)
						try:
							with transaction.atomic():
								if selected_seats and Ticket.objects.filter(order__event=event, seat_id__in=selected_seat_ids).exists():
									checkout_error = 'Salah satu kursi baru saja terisi. Silakan pilih kursi lain.'
									raise ValueError('seat_taken')

								order = Order.objects.create(
									customer=customer,
									event=event,
									total_price=total,
									quantity=quantity,
									payment_status='pending',
								)

								if promo:
									OrderPromotion.objects.create(order=order, promotion=promo)

								for index in range(quantity):
									Ticket.objects.create(
										ticket_code=_generate_ticket_code(),
										order=order,
										ticket_category=category,
										seat=selected_seats[index] if selected_seats else None,
									)
						except ValueError:
							pass

						if not checkout_error:
							messages.success(request, 'Order berhasil dibuat.')
							return redirect('orders:order_list')

	if checkout_error:
		messages.error(request, checkout_error)

	available_seats = _available_seats_for_event(selected_event)

	return render(request, 'orders/order_create.html', {
		'events': events,
		'categories': categories,
		'selected_event_id': selected_event_id,
		'selected_category_id': selected_category_id,
		'selected_event': selected_event,
		'selected_category': selected_category,
		'selected_quantity': selected_quantity,
		'promo_code': promo_code,
		'active_promos': active_promos,
		'available_seats': available_seats,
		'selected_seat_ids': selected_seat_ids,
		'role': get_user_role(request.user),
	})


@login_required
def promotion_list(request):
	role = get_user_role(request.user)
	if request.method == 'POST':
		if role != 'admin' and not request.user.is_superuser:
			messages.error(request, 'Hanya admin yang dapat mengelola promo.')
			return redirect('orders:promotion_list')

		action = request.POST.get('action', '').strip()
		promo_id = request.POST.get('promotion_id', '').strip()
		promo = Promotion.objects.filter(pk=promo_id).first() if promo_id else None

		if action == 'create':
			promo_code = request.POST.get('promo_code', '').strip().upper()
			discount_type = request.POST.get('discount_type', '').strip()
			discount_amount = request.POST.get('discount_amount', '').strip()
			start_date = _parse_date_value(request.POST.get('start_date', '').strip())
			end_date = _parse_date_value(request.POST.get('end_date', '').strip())
			quota = _parse_positive_int(request.POST.get('quota'))
			is_active = request.POST.get('is_active') == 'on'

			if not promo_code:
				messages.error(request, 'Kode promo wajib diisi.')
			elif discount_type not in dict(Promotion.DISCOUNT_TYPE_CHOICES):
				messages.error(request, 'Tipe diskon promo tidak valid.')
			elif Promotion.objects.filter(promo_code__iexact=promo_code).exists():
				messages.error(request, 'Kode promo sudah digunakan.')
			elif start_date and end_date and end_date < start_date:
				messages.error(request, 'Tanggal berakhir tidak boleh sebelum tanggal mulai.')
			else:
				try:
					discount_value = Decimal(discount_amount)
				except (InvalidOperation, TypeError):
					messages.error(request, 'Nilai diskon tidak valid.')
					return redirect('orders:promotion_list')

				if quota is None:
					messages.error(request, 'Quota promo harus berupa bilangan bulat positif.')
				elif discount_value < 0:
					messages.error(request, 'Nilai diskon tidak boleh negatif.')
				elif discount_type == Promotion.DISCOUNT_TYPE_PERCENTAGE and discount_value > 100:
					messages.error(request, 'Diskon persentase maksimal 100%.')
				else:
					Promotion.objects.create(
						promo_code=promo_code,
						discount_type=discount_type,
						discount_amount=discount_value,
						start_date=start_date,
						end_date=end_date,
						quota=quota,
						is_active=is_active,
					)
					messages.success(request, 'Promo berhasil dibuat.')

		elif action == 'update':
			if not promo:
				messages.error(request, 'Promo yang dipilih tidak ditemukan.')
			else:
				promo_code = request.POST.get('promo_code', '').strip().upper()
				discount_type = request.POST.get('discount_type', '').strip()
				discount_amount = request.POST.get('discount_amount', '').strip()
				start_date = _parse_date_value(request.POST.get('start_date', '').strip())
				end_date = _parse_date_value(request.POST.get('end_date', '').strip())
				quota = _parse_positive_int(request.POST.get('quota'))
				is_active = request.POST.get('is_active') == 'on'

				if not promo_code:
					messages.error(request, 'Kode promo wajib diisi.')
				elif discount_type not in dict(Promotion.DISCOUNT_TYPE_CHOICES):
					messages.error(request, 'Tipe diskon promo tidak valid.')
				elif Promotion.objects.exclude(pk=promo.pk).filter(promo_code__iexact=promo_code).exists():
					messages.error(request, 'Kode promo sudah digunakan oleh promo lain.')
				elif start_date and end_date and end_date < start_date:
					messages.error(request, 'Tanggal berakhir tidak boleh sebelum tanggal mulai.')
				else:
					try:
						discount_value = Decimal(discount_amount)
					except (InvalidOperation, TypeError):
						messages.error(request, 'Nilai diskon tidak valid.')
						return redirect('orders:promotion_list')

					if quota is None:
						messages.error(request, 'Quota promo harus berupa bilangan bulat positif.')
					elif discount_value < 0:
						messages.error(request, 'Nilai diskon tidak boleh negatif.')
					elif discount_type == Promotion.DISCOUNT_TYPE_PERCENTAGE and discount_value > 100:
						messages.error(request, 'Diskon persentase maksimal 100%.')
					else:
						promo.promo_code = promo_code
						promo.discount_type = discount_type
						promo.discount_amount = discount_value
						promo.start_date = start_date
						promo.end_date = end_date
						promo.quota = quota
						promo.is_active = is_active
						promo.save(update_fields=['promo_code', 'discount_type', 'discount_amount', 'start_date', 'end_date', 'quota', 'is_active'])
						messages.success(request, 'Promo berhasil diperbarui.')

		elif action == 'delete':
			if not promo:
				messages.error(request, 'Promo yang dipilih tidak ditemukan.')
			else:
				promo.delete()
				messages.success(request, 'Promo berhasil dihapus.')
		else:
			messages.error(request, 'Aksi promo tidak dikenali.')

		return redirect('orders:promotion_list')

	promos = Promotion.objects.all().order_by('promo_code')
	return render(request, 'orders/promotion_list.html', {
		'promos': promos,
		'promo_total': promos.count(),
		'promo_active': promos.filter(is_active=True).count(),
		'promo_usage': OrderPromotion.objects.count(),
		'role': role,
	})
