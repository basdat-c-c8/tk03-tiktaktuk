from django.urls import path
from accounts.views import (
    show_main, register, login_user, logout_user, choose_role,
    venue_list, create_venue, update_venue, delete_venue, profile_view, event_list, create_event, update_event, browse_events
)

app_name = 'main'

urlpatterns = [
    # 🔥 HALAMAN AWAL (WAJIB KE SINI)
    path('', choose_role, name='choose_role'),

    # 🔐 AUTH
    path('login/', login_user, name='login'),
    path('logout/', logout_user, name='logout'),
    path('register/', register, name='register'),

    # 🧠 DASHBOARD (HARUS LOGIN)
    path('dashboard/', show_main, name='show_main'),
    path('venues/', venue_list, name='venue_list'),
    path('venues/create/', create_venue, name='create_venue'),
    path('venues/<uuid:id>/edit/', update_venue, name='update_venue'),
    path('venues/<uuid:id>/delete/', delete_venue, name='delete_venue'),
    path('profile/', profile_view, name='profile'),
    path('events/', event_list, name='event_list'),
    path('events/create/', create_event, name='create_event'),
    path('events/<uuid:id>/edit/', update_event, name='update_event'),
    path('browse-events/', browse_events, name='browse_events'),
]