from django.shortcuts import render

# Create your views here.
def seat_list(request):
    return render(request, 'seat.html')