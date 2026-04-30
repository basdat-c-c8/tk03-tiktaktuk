from urllib import request
from django.shortcuts import render

# Create your views here.
def artist_list(request):
    return render(request, 'cudartist.html')
 
def artist_read(request):
    return render(request, 'rartist.html')
 
def ticket_category_manage(request):
    return render(request, 'cudticketcategory.html')
 
def ticket_category_read(request):
    return render(request, 'rticketcategory.html')