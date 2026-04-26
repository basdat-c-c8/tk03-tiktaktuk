from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from accounts.models import Venue
from django.contrib.auth.forms import PasswordChangeForm
from accounts.models import Event, Artist, TicketCategory




class VenueForm(forms.ModelForm):
    class Meta:
        model = Venue
        fields = ["venue_name", "capacity", "city", "address", "has_reserved_seating"]
        widgets = {
            "venue_name": forms.TextInput(attrs={"placeholder": "cth. Jakarta Convention Center"}),
            "capacity": forms.NumberInput(attrs={"placeholder": "1000"}),
            "city": forms.TextInput(attrs={"placeholder": "Jakarta"}),
            "address": forms.Textarea(attrs={"placeholder": "Jl. Gatot Subroto No.1", "rows": 4}),
        }

class RegisterForm(UserCreationForm):
    full_name = forms.CharField(
        label="Nama Lengkap",
        max_length=100,
        widget=forms.TextInput(attrs={"placeholder": "Masukkan nama lengkap"})
    )
    email = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(attrs={"placeholder": "Masukkan email"})
    )
    phone_number = forms.CharField(
        label="Nomor Telepon",
        max_length=15,
        widget=forms.TextInput(attrs={"placeholder": "Masukkan nomor telepon"})
    )
    username = forms.CharField(
        widget=forms.TextInput(attrs={"placeholder": "Pilih username"})
    )
    password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={"placeholder": "Minimal 8 karakter"})
    )
    password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={"placeholder": "Konfirmasi password"})
    )

    class Meta:
        model = User
        fields = ["full_name", "email", "phone_number", "username", "password1", "password2"]

class ProfileUpdateForm(forms.Form):
    full_name = forms.CharField(
        label="Nama Lengkap",
        max_length=100,
        widget=forms.TextInput(attrs={"placeholder": "Nama lengkap"})
    )
    phone_number = forms.CharField(
        label="Nomor Telepon",
        max_length=15,
        widget=forms.TextInput(attrs={"placeholder": "Nomor telepon"})
    )
    email = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(attrs={"placeholder": "Email"})
    )

class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = ["event_title", "event_datetime", "venue", "organizer", "artists", "description"]
        widgets = {
            "event_title": forms.TextInput(attrs={"placeholder": "cth. Konser Melodi Senja"}),
            "event_datetime": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "description": forms.Textarea(attrs={"placeholder": "Deskripsi acara...", "rows": 4}),
            "artists": forms.CheckboxSelectMultiple(),
        }


class TicketCategoryForm(forms.ModelForm):
    class Meta:
        model = TicketCategory
        fields = ["category_name", "quota", "price"]