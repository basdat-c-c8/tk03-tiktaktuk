from django.shortcuts import render


def ticket_list(request):
    return render(request, 'ticket_customer.html')

def ticket_admin_organizer(request):
    return render(request, 'ticket_admin_organizer.html')