from django.urls import path
from . import views

app_name = 'events'

urlpatterns = [
    # ── ARTIST ──────────────────────────────────────────────
    path('artists/',                              views.artist_list,            name='artist_list'),
    path('artists/read/',                         views.artist_read,            name='artist_read'),
    path('artists/create/',                       views.artist_create,          name='artist_create'),
    path('artists/update/<uuid:id>/',             views.artist_update,          name='artist_update'),
    path('artists/delete/<uuid:id>/',             views.artist_delete,          name='artist_delete'),

    # ── TICKET CATEGORY ─────────────────────────────────────
    path('ticket-categories/',                    views.ticket_category_read,   name='ticket_category_read'),
    path('ticket-categories/manage/',             views.ticket_category_manage, name='ticket_category_manage'),
    path('ticket-categories/create/',             views.ticket_category_create, name='ticket_category_create'),
    path('ticket-categories/update/<uuid:id>/',   views.ticket_category_update, name='ticket_category_update'),
    path('ticket-categories/delete/<uuid:id>/',   views.ticket_category_delete, name='ticket_category_delete'),
]