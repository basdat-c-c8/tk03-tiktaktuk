from django.urls import path
from . import views

app_name = 'tickets'

urlpatterns = [
    path('tickets/', views.ticket_list, name='ticket_list'),
]