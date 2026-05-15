from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from accounts.models import Event, Customer
from events.models import TicketCategory
from .models import Order, Promotion, OrderPromotion
from tickets.models import Ticket


@login_required
def order_list(request):

    if request.user.is_superuser:

        orders = Order.objects.all().order_by('-order_datetime')

    else:

        customer = Customer.objects.filter(user=request.user).first()

        if customer:
            orders = Order.objects.filter(
                customer=customer
            ).order_by('-order_datetime')

        else:
            orders = Order.objects.none()



    paid_count = orders.filter(
        payment_status__iexact='paid'
    ).count()

    pending_count = orders.filter(
        payment_status__iexact='pending'
    ).count()

    revenue = sum(
        order.total_price for order in orders
    )

    return render(request, 'orders/order_list.html', {
        'orders': orders,
        'paid_count': paid_count,
        'pending_count': pending_count,
        'revenue': revenue,
    })

@login_required
def order_create(request):
	events = Event.objects.all().order_by('-event_datetime')
	categories = TicketCategory.objects.select_related('event').all()

	if request.method == 'POST':
		event_id = request.POST.get('event')
		category_id = request.POST.get('category')
		quantity = int(request.POST.get('quantity') or 1)
		promo_code = request.POST.get('promo_code', '').strip()

		customer = Customer.objects.filter(user=request.user).first()
		if not customer:
			messages.error(request, 'Customer profile not found.')
			return redirect('main:profile')

		event = get_object_or_404(Event, pk=event_id)
		category = get_object_or_404(TicketCategory, pk=category_id)

		# price calc
		total = category.price * quantity

		promo = None
		if promo_code:
			promo = Promotion.objects.filter(promo_code__iexact=promo_code, is_active=True).first()
			if promo:
				total = total - promo.discount_amount

		order = Order.objects.create(
			customer=customer,
			event=event,
			total_price=total,
			quantity=quantity,
		)

		if promo:
			try:
				OrderPromotion.objects.create(order=order, promotion=promo)
			except Exception:
				pass

		# generate tickets
		existing = Ticket.objects.count()
		tickets = []
		for i in range(quantity):
			idx = existing + i + 1
			code = f"TKT-{idx:04d}"
			t = Ticket.objects.create(
				ticket_code=code,
				order=order,
				ticket_category=category,
			)
			tickets.append(t)

		messages.success(request, f'Order created with {len(tickets)} tickets.')
		return redirect('orders:order_list')

	return render(request, 'orders/order_create.html', {
		'events': events,
		'categories': categories,
	})


def promotion_list(request):
	promos = Promotion.objects.all()
	return render(request, 'orders/promotion_list.html', {'promos': promos})