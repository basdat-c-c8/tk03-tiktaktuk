import re
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.contrib.auth.forms import PasswordChangeForm
from accounts.models import Event, Venue
from events.models import Artist, TicketCategory

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

    def clean(self):
        cleaned_data = super().clean()
        venue_name = cleaned_data.get("venue_name")
        city = cleaned_data.get("city")

        if venue_name and city:
            duplicate = Venue.objects.filter(
                venue_name__iexact=venue_name,
                city__iexact=city
            )

            # 🔥 penting: biar update ga ke-detect sebagai duplikat dirinya sendiri
            if self.instance and self.instance.pk:
                duplicate = duplicate.exclude(pk=self.instance.pk)

            if duplicate.exists():
                existing = duplicate.first()
                raise forms.ValidationError(
                    f'ERROR: Venue "{venue_name}" di kota "{city}" sudah terdaftar dengan ID {existing.venue_id}.'
                )

        return cleaned_data

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

    def clean_username(self):
        username = self.cleaned_data.get("username")

        # CEK KARAKTER
        if not re.match(r"^[a-zA-Z0-9]+$", username):
            raise forms.ValidationError(
                f'ERROR: Username "{username}" hanya boleh mengandung huruf dan angka tanpa simbol atau spasi.'
            )

        # CEK DUPLIKAT
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError(
                f'ERROR: Username "{username}" sudah terdaftar, gunakan username lain.'
            )

        return username
        
class ProfileUpdateForm(forms.Form):
    full_name = forms.CharField(
        label="Nama Lengkap",
        max_length=100,
        widget=forms.TextInput(attrs={"placeholder": "Nama lengkap"})
    )
    phone_number = forms.CharField(
        label="Nomor Telepon",
        max_length=15,
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "Nomor telepon"})
    )
    email = forms.EmailField(
        label="Email",
        required=False,
        widget=forms.EmailInput(attrs={"placeholder": "Email"})
    )

class EventForm(forms.ModelForm):

    artists = forms.ModelMultipleChoiceField(
        queryset=Artist.objects.all().order_by("name"),
        required=False,
        widget=forms.CheckboxSelectMultiple()
    )

    class Meta:
        model = Event

        fields = [
            "event_title",
            "event_datetime",
            "venue",
            "organizer",
            "artists",
            "description"
        ]

        widgets = {
            "event_title": forms.TextInput(
                attrs={
                    "placeholder": "cth. Konser Melodi Senja"
                }
            ),

            "event_datetime": forms.DateTimeInput(
                attrs={
                    "type": "datetime-local"
                }
            ),

            "description": forms.Textarea(
                attrs={
                    "placeholder": "Deskripsi acara...",
                    "rows": 4
                }
            ),
        }


class TicketCategoryForm(forms.ModelForm):
    class Meta:
        model = TicketCategory
        fields = ["category_name", "quota", "price"]