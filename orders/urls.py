from django.urls import path
from . import views
app_name = 'orders'

urlpatterns = [
    path('orders/', views.order_list, name='order_list'),
    path('orders/create/', views.order_create, name='order_create'),
    path('promotions/', views.promotion_list, name='promotion_list'),
]
