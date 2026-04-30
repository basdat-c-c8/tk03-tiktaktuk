from django.urls import path
from . import views

app_name = 'seats'

urlpatterns = [
    path('seats/', views.seat_list, name='seat_list'),
]