from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from accounts.models import Customer
from .models import Ticket


@login_required
def ticket_list(request):
    customer = Customer.objects.filter(user=request.user).first()
    tickets = Ticket.objects.filter(order__customer=customer) if customer else []
    return render(request, 'ticket_customer.html', {'tickets': tickets})


@login_required
def ticket_admin_organizer(request):
    if request.user.is_superuser:
        tickets = Ticket.objects.all()
    else:
        customer = Customer.objects.filter(user=request.user).first()
        tickets = Ticket.objects.filter(order__customer=customer) if customer else []
    return render(request, 'ticket_admin_organizer.html', {'tickets': tickets})