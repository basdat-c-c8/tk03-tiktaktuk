from django.urls import path
from . import views

app_name = 'events'

urlpatterns = [
    path('artists/', views.artist_list, name='artist_list'),
    path('artists/read/', views.artist_read, name='artist_read'),
    path('ticket-categories/', views.ticket_category_read, name='ticket_category_read'),
    path('ticket-categories/manage/', views.ticket_category_manage, name='ticket_category_manage'),
]
 