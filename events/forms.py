from django import forms
from .models import Artist, TicketCategory


class ArtistForm(forms.ModelForm):
    class Meta:
        model  = Artist
        fields = ['name', 'genre']
        widgets = {
            'name': forms.TextInput(attrs={
                'id': 'cName',
                'placeholder': 'cth. Fourtwnty',
                'autocomplete': 'off',
            }),
            'genre': forms.TextInput(attrs={
                'id': 'cGenre',
                'placeholder': 'cth. Indie Folk',
                'autocomplete': 'off',
            }),
        }
        error_messages = {
            'name': {'required': 'Nama artis wajib diisi.'},
        }


class TicketCategoryForm(forms.ModelForm):
    class Meta:
        model  = TicketCategory
        fields = ['category_name', 'price', 'quota', 'event']
        widgets = {
            'category_name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'cth. VIP',
            }),

            'price': forms.NumberInput(attrs={
                'class': 'form-input',
                'placeholder': '750000',
            }),

            'quota': forms.NumberInput(attrs={
                'class': 'form-input',
                'placeholder': '100',
            }),

            'event': forms.Select(attrs={
                'class': 'form-select',
            }),
        }
        error_messages = {
            'category_name': {'required': 'Nama kategori wajib diisi.'},
            'price':         {'required': 'Harga wajib diisi.'},
            'quota':         {'required': 'Kuota wajib diisi.'},
            'event':         {'required': 'Acara wajib dipilih.'},
        }

    def clean_quota(self):
        quota = self.cleaned_data.get('quota')
        if quota is not None and quota < 1:
            raise forms.ValidationError('Kuota harus bilangan bulat positif (> 0).')
        return quota

    def clean_price(self):
        price = self.cleaned_data.get('price')
        if price is not None and price < 0:
            raise forms.ValidationError('Harga tidak valid (harus ≥ 0).')
        return price