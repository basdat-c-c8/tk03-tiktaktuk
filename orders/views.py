from django.shortcuts import render

# Create your views here.


def order_list(request):
	return render(request, 'orders/order_list.html')


def order_create(request):
	return render(request, 'orders/order_create.html')


def promotion_list(request):
	return render(request, 'orders/promotion_list.html')
