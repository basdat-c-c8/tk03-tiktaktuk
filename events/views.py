from urllib import request
from django.shortcuts import render

# Create your views here.
def artist_list(request):
    return render(request, 'events/RArtist.html')

def ticket_category_list(request):
    return render(request, 'events/CUDTicketCategory.html')

def ticket_category_manage(request):
    return render(request, 'events/CUDTicketCategory.html')

def ticket_category_read(request):
    return render(request, 'events/RTicketCategory.html')