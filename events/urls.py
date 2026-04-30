from django.urls import path
from . import views

app_name = 'events'

urlpatterns = [
    path('artists/', views.artist_list, name='artist_list'),
    # Artist API endpoints (AJAX)
    path('artists/create/', views.artist_create, name='artist_create'),
    path('artists/<uuid:artist_id>/update/', views.artist_update, name='artist_update'),
    path('artists/<uuid:artist_id>/delete/', views.artist_delete, name='artist_delete'),
    path('artists/<uuid:artist_id>/detail/', views.artist_detail, name='artist_detail'),
    path('ticket-categories/manage/', views.ticket_category_manage, name='ticket_category_manage'),
    path('ticket-categories/', views.ticket_category_read, name='ticket_category_read'),
]