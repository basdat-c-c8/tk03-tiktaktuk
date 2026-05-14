from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from django.contrib import messages
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import HttpResponseRedirect
from django.urls import reverse
import datetime
from django.utils import timezone
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from accounts.models import Event
import re

from accounts.forms import RegisterForm, VenueForm, ProfileUpdateForm, EventForm
from accounts.models import (
    Role,
    AccountRole,
    Customer,
    Organizer,
    Venue,
    Event,
)

from events.models import Artist, TicketCategory

def get_user_role(user):
    if user.is_superuser:
        return "admin"

    account_role = AccountRole.objects.filter(user=user).first()

    if account_role:
        return account_role.role.role_name

    return "pelanggan"


@login_required(login_url='/login')
def show_main(request):
    role = get_user_role(request.user)

    if role == "admin":
        return redirect("main:admin_dashboard")
    elif role == "penyelenggara":
        return redirect("main:organizer_dashboard")
    else:
        return redirect("main:customer_dashboard")


@login_required(login_url='/login')
def admin_dashboard(request):
    venues = Venue.objects.all()

    largest_capacity = 0
    if venues.exists():
        largest_capacity = venues.order_by("-capacity").first().capacity

    context = {
        "name": request.user.username,
        "role": "admin",
        "last_login": request.COOKIES.get("last_login", "Never"),

        "total_users": User.objects.count(),
        "total_events": Event.objects.count(),
        "total_venue": venues.count(),
        "reserved_count": venues.filter(has_reserved_seating=True).count(),
        "largest_capacity": largest_capacity,
    }

    return render(request, "dashboard_admin.html", context)


@login_required(login_url='/login')
def organizer_dashboard(request):

    events = Event.objects.all().order_by("-event_datetime")
    venues = Venue.objects.all()

    context = {
        "name": request.user.username,
        "role": "penyelenggara",
        "last_login": request.COOKIES.get("last_login", "Never"),

        "events": events,
        "total_events": events.count(),
        "total_venues": venues.count(),
    }

    return render(
        request,
        "dashboard_organizer.html",
        context
    )


@login_required(login_url='/login')
def customer_dashboard(request):
    context = {
        "name": request.user.username,
        "role": "pelanggan",
        "last_login": request.COOKIES.get("last_login", "Never"),
    }

    return render(request, "dashboard_customer.html", context)


def register(request):
    role = request.GET.get("role", "pelanggan")

    if role == "penyelenggara":
        role_title = "Daftar sebagai Penyelenggara"
    elif role == "admin":
        role_title = "Daftar sebagai Admin"
    else:
        role_title = "Daftar sebagai Pelanggan"

    form = RegisterForm()

    if request.method == "POST":

        form = RegisterForm(request.POST)

        username = request.POST.get("username", "").strip()

        # VALIDASI KARAKTER
        if not re.match(r'^[A-Za-z0-9]+$', username):

            messages.error(
                request,
                f'ERROR: Username "{username}" hanya boleh mengandung huruf dan angka tanpa simbol atau spasi.'
            )

            context = {
                "form": form,
                "role": role,
                "role_title": role_title,
            }

            return render(request, "register.html", context)

        # VALIDASI DUPLIKAT CASE-INSENSITIVE
        if User.objects.filter(username__iexact=username).exists():

            messages.error(
                request,
                f'ERROR: Username "{username}" sudah terdaftar, gunakan username lain.'
            )

            context = {
                "form": form,
                "role": role,
                "role_title": role_title,
            }

            return render(request, "register.html", context)

        if form.is_valid():

            user = form.save(commit=False)

            user.username = username
            user.email = form.cleaned_data["email"]
            user.first_name = form.cleaned_data["full_name"]

            user.save()

            role_obj, created = Role.objects.get_or_create(
                role_name=role
            )

            AccountRole.objects.create(
                user=user,
                role=role_obj
            )

            if role == "pelanggan":

                Customer.objects.create(
                    user=user,
                    full_name=form.cleaned_data["full_name"],
                    phone_number=form.cleaned_data["phone_number"]
                )

            elif role == "penyelenggara":

                Organizer.objects.create(
                    user=user,
                    organizer_name=form.cleaned_data["full_name"],
                    contact_email=form.cleaned_data["email"]
                )

            messages.success(
                request,
                "Akun berhasil dibuat!"
            )

            return redirect("main:login")

    context = {
        "form": form,
        "role": role,
        "role_title": role_title,
    }

    return render(
        request,
        "register.html",
        context
    )


def login_user(request):
    form = AuthenticationForm(request, data=request.POST or None)

    form.fields["username"].widget.attrs.update({
        "placeholder": "Masukkan username"
    })

    form.fields["password"].widget.attrs.update({
        "placeholder": "Masukkan password"
    })

    if request.method == "POST":
        if form.is_valid():
            user = form.get_user()
            login(request, user)

            response = HttpResponseRedirect(reverse("main:show_main"))
            response.set_cookie("last_login", str(datetime.datetime.now()))
            return response

    return render(request, "login.html", {"form": form})


def logout_user(request):
    logout(request)

    response = HttpResponseRedirect(reverse("main:login"))
    response.delete_cookie("last_login")

    return response


def choose_role(request):
    return render(request, "choose_role.html")


@login_required(login_url='/login')
def venue_list(request):
    role = get_user_role(request.user)

    venues = Venue.objects.all()

    q = request.GET.get("q")
    city = request.GET.get("city")
    seating = request.GET.get("seating")

    if q:
        venues = venues.filter(venue_name__icontains=q) | venues.filter(address__icontains=q)

    if city:
        venues = venues.filter(city=city)

    if seating == "reserved":
        venues = venues.filter(has_reserved_seating=True)
    elif seating == "free":
        venues = venues.filter(has_reserved_seating=False)

    all_venues = Venue.objects.all()

    context = {
        "venues": venues,
        "role": role,
        "total_venue": all_venues.count(),
        "reserved_count": all_venues.filter(has_reserved_seating=True).count(),
        "total_capacity": sum(v.capacity for v in all_venues),
        "cities": all_venues.values_list("city", flat=True).distinct(),
    }

    return render(request, "venue_list.html", context)



@login_required(login_url='/login')
@login_required(login_url='/login')
def create_venue(request):
    role = get_user_role(request.user)

    if role not in ["admin", "penyelenggara"]:
        return redirect("main:show_main")

    form = VenueForm(request.POST or None)

    if request.method == "POST":

        venue_name = request.POST.get("venue_name", "").strip()
        city = request.POST.get("city", "").strip()

        existing_venue = Venue.objects.filter(
            venue_name__iexact=venue_name,
            city__iexact=city
        ).first()

        if existing_venue:

            messages.error(
                request,
                    f'ERROR: Venue "{venue_name}" di kota "{city}" sudah terdaftar.'
            )

        elif form.is_valid():

            form.save()

            messages.success(
                request,
                "Venue berhasil ditambahkan."
            )

            return redirect("main:venue_list")

    context = {
        "form": form,
        "title": "Tambah Venue Baru",
        "button_text": "Tambah",
    }

    return render(request, "venue_form.html", context)


@login_required(login_url='/login')
def update_venue(request, id):
    role = get_user_role(request.user)

    if role not in ["admin", "penyelenggara"]:
        return redirect("main:show_main")

    venue = get_object_or_404(Venue, venue_id=id)

    form = VenueForm(request.POST or None, instance=venue)

    if request.method == "POST":

        if form.is_valid():

            venue_name = form.cleaned_data["venue_name"].strip()
            city = form.cleaned_data["city"].strip()

            existing_venue = Venue.objects.filter(
                venue_name__iexact=venue_name,
                city__iexact=city
            ).exclude(venue_id=venue.venue_id).first()

            if existing_venue:
                messages.error(
                    request,
                    f'ERROR: Venue "{venue_name}" di kota "{city}" sudah terdaftar dengan ID {existing_venue.venue_id}.'
                )

            else:
                form.save()
                messages.success(request, "Venue berhasil diperbarui.")
                return redirect("main:venue_list")

    context = {
        "form": form,
        "title": "Edit Venue",
        "button_text": "Simpan",
    }

    return render(request, "venue_form.html", context)

@login_required(login_url='/login')
def delete_venue(request, id):
        role = get_user_role(request.user)
        if role not in ["admin", "penyelenggara"]:
            return redirect("main:show_main")

        venue = get_object_or_404(Venue, venue_id=id)

        # cek apakah masih ada event aktif / upcoming
        active_event_exists = Event.objects.filter(
            venue=venue,
            event_datetime__gte=timezone.now()
        ).exists()

        # jika masih ada event aktif → tidak boleh dihapus
        if active_event_exists:
            messages.error(
                request,
                f'ERROR: Venue "{venue.venue_name}" masih memiliki event aktif sehingga tidak dapat dihapus.'
            )

            return redirect("main:venue_list")

        # proses hapus
        if request.method == "POST":
            venue.delete()

            messages.success(
                request,
                f'Venue "{venue.venue_name}" berhasil dihapus.'
            )

            return redirect("main:venue_list")

        return render(request, "venue_confirm_delete.html", {
            "venue": venue
        })


@login_required(login_url='/login')
def profile_view(request):
    role = get_user_role(request.user)

    profile_form = ProfileUpdateForm(initial={
        "full_name": request.user.first_name,
        "email": request.user.email,
        "phone_number": Customer.objects.filter(user=request.user).first().phone_number
        if Customer.objects.filter(user=request.user).exists()
        else "",
    })

    password_form = PasswordChangeForm(request.user)

    if request.method == "POST":
        if "update_profile" in request.POST:
            profile_form = ProfileUpdateForm(request.POST)

            if profile_form.is_valid():
                if role == "pelanggan":
                    customer, created = Customer.objects.get_or_create(
                        user=request.user,
                        defaults={
                            "full_name": profile_form.cleaned_data["full_name"],
                            "phone_number": profile_form.cleaned_data["phone_number"],
                        }
                    )

                    customer.full_name = profile_form.cleaned_data["full_name"]
                    customer.phone_number = profile_form.cleaned_data["phone_number"]
                    customer.save()

                    request.user.first_name = profile_form.cleaned_data["full_name"]
                    request.user.email = profile_form.cleaned_data["email"]
                    request.user.save()

                elif role == "penyelenggara":
                    organizer, created = Organizer.objects.get_or_create(
                        user=request.user,
                        defaults={
                            "organizer_name": profile_form.cleaned_data["full_name"],
                            "contact_email": profile_form.cleaned_data["email"],
                        }
                    )

                    organizer.organizer_name = profile_form.cleaned_data["full_name"]
                    organizer.contact_email = profile_form.cleaned_data["email"]
                    organizer.save()

                    request.user.first_name = profile_form.cleaned_data["full_name"]
                    request.user.email = profile_form.cleaned_data["email"]
                    request.user.save()

                elif role == "admin":
                    request.user.first_name = profile_form.cleaned_data["full_name"]
                    request.user.email = profile_form.cleaned_data["email"]
                    request.user.save()

                messages.success(request, "Profil berhasil diperbarui.")
                return redirect("main:profile")

        elif "update_password" in request.POST:
            password_form = PasswordChangeForm(request.user, request.POST)

            if password_form.is_valid():
                user = password_form.save()
                update_session_auth_hash(request, user)
                messages.success(request, "Password berhasil diperbarui.")
                return redirect("main:profile")

    context = {
        "role": role,
        "profile_form": profile_form,
        "password_form": password_form,
    }

    return render(request, "profile.html", context)


@login_required(login_url='/login')
@login_required(login_url='/login')
@login_required(login_url='/login')
def event_list(request):

    role = get_user_role(request.user)

    events = Event.objects.select_related(
        "venue",
        "organizer"
    ).all()

    # SEARCH
    search = request.GET.get("search")

    if search:
        events = events.filter(
            event_title__icontains=search
        )

    # FILTER KOTA
    city = request.GET.get("city")

    if city:
        events = events.filter(
            venue__city=city
        )

    # FILTER SEATING
    seating = request.GET.get("seating")

    if seating == "reserved":
        events = events.filter(
            venue__has_reserved_seating=True
        )

    elif seating == "free":
        events = events.filter(
            venue__has_reserved_seating=False
        )

    # DATA DROPDOWN
    cities = Venue.objects.values_list(
        "city",
        flat=True
    ).distinct()

    context = {
        "events": events,
        "role": role,
        "cities": cities,
    }

    return render(
        request,
        "event_list.html",
        context
    )

@login_required(login_url='/login')
def create_event(request):
    role = get_user_role(request.user)

    if role not in ["admin", "penyelenggara"]:
        return redirect("main:show_main")

    form = EventForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        event = form.save()

        category_names = request.POST.getlist("category_name[]")
        prices = request.POST.getlist("price[]")
        quotas = request.POST.getlist("quota[]")

        for i in range(len(category_names)):
            if category_names[i] and prices[i] and quotas[i]:
                TicketCategory.objects.create(
                    event=event,
                    category_name=category_names[i],
                    price=prices[i],
                    quota=quotas[i]
                )

        return redirect("main:event_list")

    return render(request, "event_form.html", {
        "form": form,
        "title": "Buat Acara Baru",
        "button_text": "Buat Acara",
    })


@login_required(login_url='/login')
def update_event(request, id):
    event = get_object_or_404(Event, pk=id)

    role = get_user_role(request.user)
    if role not in ["admin", "penyelenggara"]:
        return redirect("main:show_main")

    form = EventForm(request.POST or None, instance=event)

    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("main:event_list")

    return render(request, "event_form.html", {
        "form": form,
        "title": "Edit Acara",
        "button_text": "Simpan",
    })


@login_required(login_url='/login')
def browse_events(request):
    q = request.GET.get("q", "")
    venue_id = request.GET.get("venue", "")
    artist_id = request.GET.get("artist", "")

    events = Event.objects.all().order_by("-event_datetime")

    if q:
        events = events.filter(event_title__icontains=q)

    if venue_id:
        events = events.filter(venue__venue_id=venue_id)

    if artist_id:
        events = events.filter(artists__artist_id=artist_id)

    context = {
        "events": events,
        "venues": Venue.objects.all(),
        "artists": Artist.objects.all(),
        "q": q,
        "selected_venue": venue_id,
        "selected_artist": artist_id,
    }

    return render(request, "browse_event.html", context)


def create_pengguna(request):
    return render(request, "cpengguna.html")