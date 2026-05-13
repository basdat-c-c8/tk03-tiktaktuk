from django.urls import path
from . import views

app_name = 'events'

urlpatterns = [
    path('artists/', views.artist_list, name='artist_list'),
    path('artists/create/', views.create_artist, name='create_artist'),
    path('artists/update/<uuid:id>/', views.update_artist, name='update_artist'),
    path('artists/delete/<uuid:id>/', views.delete_artist, name='delete_artist'),
    path('artists/read/', views.artist_read, name='artist_read'),
    path('ticket-categories/', views.ticket_category_read, name='ticket_category_read'),
    path('ticket-categories/manage/', views.ticket_category_manage, name='ticket_category_manage'),
]