from django.shortcuts import render

# Create your views here.
def ticket_list(request):
    if request.user.role == 'customer':
        return render(request, 'ticket_customer.html')
    else:
        return render(request, 'ticket_admin.html')