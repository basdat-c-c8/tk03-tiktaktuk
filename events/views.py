from urllib import request
from django.shortcuts import render

# Create your views here.
def artist_list(request):
    return render(request, 'events/templates/cudartist.html')
 
def artist_read(request):
    return render(request, 'events/rartist.html')
 
def ticket_category_manage(request):
    return render(request, 'events/templates/cudticketcategory.html')
 
def ticket_category_read(request):
    return render(request, 'events/rticketcategory.html')