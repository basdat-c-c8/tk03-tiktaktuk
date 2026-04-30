from django.shortcuts import render


def ticket_list(request):
    if request.user.role == 'customer':
        return render(request, 'ticket_customer.html')
    else:
        return render(request, 'ticket_admin_organisasi.html')